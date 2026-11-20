"""Amendment 010: a single stationary P0 history shared by all policies."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from a16_generator import ROOT, SEED, START, load_design, preserve_mean, renewal_path, sha
from a9_observations import observable_spells
from round5_execution import atomic_json, check_historical, freeze

OUT = ROOT / 'data/derived/a9/warmup'
PHASES = {'verification': 0, 'pilot': 1, 'main': 2}
LEVELS = {'calibrated': 0, 'null': 1, 'amplified': 2}
POLICIES = ('P0', 'P1', 'P2', 'P3', 'P2_fixed', 'P2_age')
SHIFT_DAYS = 365


class RenewalExponential:
    """One independent threshold per (renewal,risk), including the losing risk."""
    def __init__(self, key, risk):
        self.key, self.risk, self.renewal = list(key), risk, 0

    def exponential(self):
        key = [SEED, *self.key, self.renewal, self.risk]
        self.renewal += 1
        return float(np.random.default_rng(np.random.SeedSequence(key)).exponential())


def parameters(truth, level):
    beta = truth.beta.to_numpy().copy()
    if level == 'null':
        beta[:] = 1.
    elif level == 'amplified':
        beta = 1 + 1.5 * (beta - 1)
    elif level != 'calibrated':
        raise ValueError('Unknown beta level')
    return beta, preserve_mean(truth.beta.to_numpy(), truth.eta.to_numpy(), beta)


def auxiliary_flights(flights):
    dates = pd.to_datetime(flights['Flight Date'], format='%d/%m/%Y')
    select = dates.ge(START) & dates.lt(START + pd.DateOffset(years=1))
    result = flights.loc[select, ['Aircraft #', 'Flight Date', 'Hours', 'Take Off']].copy()
    result['Flight Date'] = (dates[select] - pd.Timedelta(days=SHIFT_DAYS)).dt.strftime('%d/%m/%Y')
    result['Aircraft #'] = result['Aircraft #'] + '-AUX'
    return result.reset_index(drop=True)


def generate(replicate, level, phase, truth, channels, flights):
    """No policy, r, utilisation-knowledge or scenario argument is accepted."""
    if phase not in PHASES or level not in LEVELS or replicate < 0:
        raise ValueError('Invalid warmup key')
    beta, eta = parameters(truth, level)
    final = (START + pd.DateOffset(years=1) - pd.Timedelta(days=1) - START).days
    rows, incomplete, used = [], 0, 0
    for channel in channels:
        intervals = [(max(0, a), min(final, b)) for a, b in channel['intervals']
                     if max(0, a) < min(final, b)]
        if not intervals:
            continue
        used += 1
        p = channel['pn_index']
        ac = int(channel['aircraft'].split('-')[1])
        key = [90, PHASES[phase], LEVELS[level], replicate, p, ac, channel['channel']]
        path = list(renewal_path(channel['curve'], intervals[0][0], intervals[-1][1],
                    beta[p], eta[p], float(truth.iloc[p].nu),
                    RenewalExponential(key, 1), RenewalExponential(key, 2)))
        unit = f'AUX-{p}-{ac}-{channel["channel"]}'
        for observation, (left, right) in enumerate(intervals):
            for renewal, (birth, end, risk, _) in enumerate(path):
                if end <= left or birth >= right:
                    continue
                if birth < left:
                    incomplete += 1
                    continue
                observed_end = min(end, right)
                observed_risk = risk if end <= right else 0
                rows.append(dict(pn=channel['pn'], aircraft=channel['aircraft'] + '-AUX',
                    unit=unit + '-' + str(observation), renewal=renewal,
                    start=birth - SHIFT_DAYS, end=observed_end - SHIFT_DAYS,
                    censor_end=observed_end - SHIFT_DAYS, risk=observed_risk))
    spells = observable_spells(rows, [], START, final - SHIFT_DAYS)
    spells['spell_id'] = ['AUX-' + str(i).zfill(8) for i in range(len(spells))]
    spells['cohort'] = 'auxiliary'
    spells['evaluate'] = False
    shifted = auxiliary_flights(flights)
    metadata = dict(seed_study=90, phase=phase, level=level, replicate=replicate,
        shift_days=SHIFT_DAYS, reference_policy='P0', independent_of_evaluation=True,
        auxiliary_channels=used, unavailable_first_year_channels=len(channels) - used,
        incomplete_observation_segments_excluded=incomplete, spells=len(spells),
        events=int(spells.event.sum()), preventive_events=int(spells.preventive.sum()),
        auxiliary_evaluated=False, retained_at_all_training_origins=True,
        first_observation_date=str(spells.att.min()), last_observation_date=str(spells.rem.max()))
    return spells, shifted, metadata


def initialise_configuration():
    original = json.loads((ROOT / 'data/derived/a16/flow17/configuration.json').read_text())
    check_historical(original['historical'])
    names = ['analysis/emenda_A16_A9_010.md', 'analysis/a9_warmup.py',
             'analysis/a9_observations.py', 'analysis/a16_generator.py',
             'data/anonymised/hours_flown.csv', 'data/derived/a16/generator/truth.csv',
             'data/derived/a16/generator/channels.csv', 'data/derived/spells.csv']
    specification = dict(shift_days=SHIFT_DAYS, seed=SEED, seed_study=90,
        phases=PHASES, levels=LEVELS, reference_policy='P0', policies=list(POLICIES),
        cohort_continues_into_evaluation=False, retained_at_all_training_origins=True,
        sources={name: sha(ROOT / name) for name in names}, historical=original['historical'])
    OUT.mkdir(parents=True, exist_ok=True)
    return freeze(OUT / 'configuration.json', specification)


def verify_configuration():
    configuration = json.loads((OUT / 'configuration.json').read_text())
    for name, digest in configuration['sources'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Warmup source changed after freezing: ' + name)
    return configuration


def materialise(replicate, level, phase, destination=None):
    configuration = verify_configuration()
    destination = destination or OUT / 'replicas'
    folder = Path(destination) / f'{phase}_{level}_{replicate:04d}'
    manifest_path = folder / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['configuration_sha256'] != configuration['configuration_sha256']:
            raise RuntimeError('Existing warmup belongs to another frozen configuration')
        for name, digest in manifest['outputs'].items():
            if sha(folder / name) != digest:
                raise RuntimeError('Stored auxiliary history hash differs: ' + name)
        return folder
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Incomplete warmup output must be preserved, not regenerated')
    # Marker and input configuration precede every auxiliary observation.
    folder.mkdir(parents=True, exist_ok=True)
    atomic_json(folder / 'generation_started.json', dict(
        configuration_sha256=configuration['configuration_sha256'],
        phase=phase, level=level, replicate=replicate))
    truth, _, _, channels, _, _ = load_design()
    flights = pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv')
    spells, clocks, metadata = generate(replicate, level, phase, truth, channels, flights)
    spells.to_csv(folder / 'spells.csv', index=False, lineterminator='\n')
    clocks.to_csv(folder / 'flights.csv', index=False, lineterminator='\n')
    manifest = dict(**metadata, configuration_sha256=configuration['configuration_sha256'],
                    outputs={name: sha(folder / name) for name in ('spells.csv', 'flights.csv')})
    atomic_json(manifest_path, manifest)
    check_historical(configuration['historical'])
    return folder


class SharedWarmup:
    """Loaded once per replica; policies receive independent copies of identical rows."""
    def __init__(self, folder):
        self.folder = Path(folder)
        self.manifest = json.loads((self.folder / 'manifest.json').read_text())
        for name, digest in self.manifest['outputs'].items():
            if sha(self.folder / name) != digest:
                raise RuntimeError('Corrupted shared auxiliary history')
        self._spells = pd.read_csv(self.folder / 'spells.csv', parse_dates=['att', 'rem'],
                                   float_precision='round_trip')
        self._flights = pd.read_csv(self.folder / 'flights.csv', float_precision='round_trip')

    def for_policy(self, policy):
        if policy not in POLICIES:
            raise ValueError('Unknown A9 policy')
        return self._spells.copy(deep=True), self._flights.copy(deep=True)


def training_inputs(shared, policy, evaluated_spells, evaluated_flights):
    auxiliary, clocks = shared.for_policy(policy)
    real = evaluated_spells.copy()
    real['cohort'], real['evaluate'] = 'evaluation', True
    if real['Aircraft #'].astype(str).str.endswith('-AUX').any():
        raise ValueError('Auxiliary unit cannot enter evaluation')
    combined = auxiliary.copy() if real.empty else pd.concat([auxiliary, real], ignore_index=True)
    if combined.spell_id.duplicated().any():
        raise ValueError('Auxiliary/evaluation spell identifiers overlap')
    return combined, pd.concat([clocks, evaluated_flights], ignore_index=True)


def evaluation_only(frame):
    if 'cohort' not in frame:
        raise ValueError('Evaluation requires an explicit cohort label')
    if not set(frame.cohort.unique()).issubset({'auxiliary', 'evaluation'}):
        raise ValueError('Unknown cohort in evaluation')
    return frame.loc[frame.cohort.eq('evaluation')].copy()
