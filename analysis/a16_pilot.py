"""Timing-only five-replicate pilot, gated by generator validation."""
import hashlib
import json
import math
import time

import numpy as np
import pandas as pd
import psutil

from a16_generator import (ROOT, OUT, SEED, committed_protocol,
                          load_design, preserve_mean, renewal_path, sha)
from a15_stability import protected_hashes
from a4_validation import HierarchicalEvaluation
from a5_validation import KEYS, bootstrap_decision, metrics
from a5_models import START


class PilotEvaluation(HierarchicalEvaluation):
    """Exact common training calculation, reused only between the two forecasts."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shared_training = {}

    def prepare(self, origin, variant):
        if variant not in ('principal', 'realized_fh'):
            raise ValueError('Pilot cache supports only identical training variants')
        if origin not in self._shared_training:
            self._shared_training[origin] = super().prepare(origin, 'principal')
        return self._shared_training[origin]


def synthetic_inputs(replicate, truth, channels, copies=4, level='calibrated',
                     seed_study=160, seed_cell=0):
    beta = truth.beta.to_numpy().copy()
    if level == 'null':
        beta[:] = 1.
    elif level == 'amplified':
        beta = 1 + 1.5 * (beta - 1)
    elif level != 'calibrated':
        raise ValueError('Unknown beta level')
    eta = preserve_mean(truth.beta.to_numpy(), truth.eta.to_numpy(), beta)
    records, incomplete = [], 0
    for copy in range(copies):
        for channel in channels:
            p = channel['pn_index']
            aircraft = f'{channel["aircraft"]}-R{copy + 1:02d}'
            if seed_study == 160:
                if seed_cell != 0:
                    raise ValueError('Historical pilot seed has no cell axis')
                key = [SEED, 160, replicate, p, int(channel['aircraft'].split('-')[1]), channel['channel'], copy]
            else:
                key = [SEED, seed_study, seed_cell, replicate, p,
                       int(channel['aircraft'].split('-')[1]), channel['channel'], copy]
            path = list(renewal_path(channel['curve'], channel['start'], channel['end'], beta[p], eta[p],
                float(truth.iloc[p].nu), np.random.default_rng(np.random.SeedSequence(key + [1])),
                np.random.default_rng(np.random.SeedSequence(key + [2]))))
            for observation_start, observation_end in channel['intervals']:
                for renewal, (start, end, risk, _) in enumerate(path):
                    if end <= observation_start or start >= observation_end:
                        continue
                    if start < observation_start:
                        incomplete += 1
                        continue
                    observed_end = min(end, observation_end)
                    observed_removal = end <= observation_end and risk != 0
                    # A4 clocks are indexed by dates, never latent fractional age.
                    att = START + pd.Timedelta(days=int(math.ceil(start)))
                    rem = START + pd.Timedelta(days=int(math.ceil(observed_end)))
                    records.append({'Part #': channel['pn'], 'Serial #': f'SIM-{copy}-{p}-{channel["channel"]}-{renewal}',
                        'Aircraft #': aircraft, 'att': att, 'rem': rem,
                        'event': int(observed_removal and risk == 1),
                        'source': 'in_window_removed' if observed_removal else 'in_window_censored'})
    spells = pd.DataFrame(records)
    spells['spell_id'] = [f'SIM-{i:07d}' for i in range(len(spells))]
    original = pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv')
    flights = []
    for copy in range(copies):
        frame = original.copy()
        frame['Aircraft #'] = frame['Aircraft #'] + f'-R{copy + 1:02d}'
        flights.append(frame)
    return spells, pd.concat(flights, ignore_index=True), incomplete


def replica(replicate, truth, channels):
    spells, flights, incomplete = synthetic_inputs(replicate, truth, channels)
    domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
    # Only principal/realized_fh are run; inspection/provenance/admin variants are absent.
    removals = pd.DataFrame(columns=['Attached Part #', 'Attached Serial #', 'Aircraft #', 'rem'])
    admin = pd.DataFrame(columns=KEYS)
    tasks = pd.DataFrame(columns=['Aircraft #', 'Task #', 'd'])
    mapping = pd.read_csv(ROOT / 'config/rotor_inspection_map.csv')
    engine = PilotEvaluation(spells, flights, domain.pn.tolist(), tasks, mapping, removals, admin, domain=domain)
    for variant in ('principal', 'realized_fh'):
        predictions = engine.run_variant(variant)
        metrics(predictions)
        # Do not open or export effects/rejection tables from timing pilot.
        for criterion in ('K2-A4', 'K2-idade'):
            paired = predictions.copy()
            if criterion == 'K2-idade':
                paired['baseline'] = paired.e_selected
            bootstrap_decision(paired, engine.exposure.aircraft, engine.candidates, reps=999)
    return len(spells), incomplete


def main():
    revision, protocol_hash = committed_protocol()
    validation = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    verification_path = ROOT / 'data/derived/a16/verification.json'
    verification = json.loads(verification_path.read_text(encoding='utf-8'))
    if not validation['gate_passed'] or not verification['protected_files_unchanged']:
        raise RuntimeError('Generator has not passed validation and preservation checks')
    if validation['protected']['analysis/preregistro_A16_A9.md'] != protocol_hash:
        raise RuntimeError('Pilot protocol differs from validated protocol')
    before = protected_hashes()
    truth, _, _, channels, _, _ = load_design()
    rows = []
    for replicate in range(5):
        print('Timing pilot', replicate + 1, 'of 5; no effect tables will be inspected', flush=True)
        started = time.perf_counter()
        count, incomplete = replica(replicate, truth, channels)
        elapsed = time.perf_counter() - started
        memory = psutil.Process().memory_info()
        rows.append(dict(replicate=replicate, seconds=elapsed,
            process_peak_bytes=int(getattr(memory, 'peak_wset', memory.rss)),
            synthetic_spells=count, incomplete_fragments_excluded=incomplete))
        pd.DataFrame(rows).to_csv(ROOT / 'data/derived/a16/pilot_timing.csv', index=False)
        print('Completed timing pilot', replicate + 1, 'seconds', round(elapsed, 2), flush=True)
    raw_r = 50 * math.floor(48 * 3600 / (9 * 1.5 * max(r['seconds'] for r in rows)) / 50)
    budget_passed = raw_r >= 200
    fixed_r = min(raw_r, 1000) if budget_passed else None
    unchanged = before == protected_hashes() and committed_protocol() == (revision, protocol_hash)
    if not unchanged:
        raise RuntimeError('Protected artifacts changed during pilot')
    manifest = dict(protocol_revision=revision, protocol_sha256=protocol_hash, pilot_replicates=5,
        pilot_in_results=False, fleet_multiplier=4, budget_A16_hours=48, budget_A9_hours=120,
        worst_replica_seconds=max(r['seconds'] for r in rows), raw_R=raw_r, fixed_R=fixed_r,
        budget_passed=budget_passed, minimum_replicates=200, reserve_factor=1.5,
        effects_inspected=False, power_executed=False, a9_executed=False,
        protected_files_unchanged=unchanged, seed_study=160,
        pilot_timing_sha256=sha(ROOT / 'data/derived/a16/pilot_timing.csv'))
    manifest['configuration_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    (ROOT / 'data/derived/a16/pilot_manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Pilot budget passes' if budget_passed else 'STOP: R >= 200 does not fit the A16 budget', flush=True)
    return 0 if budget_passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
