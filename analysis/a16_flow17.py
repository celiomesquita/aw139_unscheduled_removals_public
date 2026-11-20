"""T16: corrected A16, fresh flow 17, original statistics and multicore coordinator."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from datetime import datetime
import json
import multiprocessing
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import pandas as pd
import psutil

import a16_power as core
import a16_multicore as parallel
from a16_generator import ROOT, load_design, sha
from a16_pilot import synthetic_inputs as original_synthetic_inputs
from exposure_errata import CorrectedA4, ObservedExposure
from round5_execution import amendment006, atomic_json, check_historical, freeze, historical_hashes

OUT = ROOT / 'data/derived/a16/flow17'
OP_SOURCES = ('analysis/a16_flow17.py', 'analysis/exposure_errata.py',
              'analysis/round5_execution.py', 'analysis/emenda_A16_A9_007.md')
_DESIGN = None
_TELEMETRY = False


class CorrectedSharedTraining(CorrectedA4):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.common_training = {}

    def prepare(self, origin, variant):
        if variant not in ('principal', 'realized_fh'):
            raise ValueError('Unexpected A16 variant')
        if origin not in self.common_training:
            self.common_training[origin] = super().prepare(origin, 'principal')
        return self.common_training[origin]


def synthetic_flow17(*args, **kwargs):
    kwargs['seed_study'] = 17
    return original_synthetic_inputs(*args, **kwargs)


def historical_budget():
    old = ROOT / 'data/derived/a16/power'
    state = json.loads((old / 'state.json').read_text(encoding='utf-8'))
    runtime = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((old / 'replicas').glob('*/*/runtime.json'))]
    pilot = pd.read_csv(ROOT / 'data/derived/a16/pilot_timing.csv')
    wall = (datetime.fromisoformat(state['finished_utc']) -
            datetime.fromisoformat(state['original_started_utc'])).total_seconds()
    return dict(old_primary_wall_seconds=wall, old_recorded_worker_seconds=sum(r['seconds'] for r in runtime),
        old_runtime_records=len(runtime), old_completed_replicas=state['completed_replicas'],
        old_missing_runtime_records=state['completed_replicas'] - len(runtime),
        pilot_seconds=float(pilot.seconds.sum()), missing_times_not_imputed=True,
        generator_and_diagnostic_costs='Recorded separately in audit; not invented where no precise timing was stored')


def threshold_equivalence():
    flights = pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv')
    exposure = ObservedExposure(flights)
    rows = []
    for origin in pd.date_range('2025-01-01', '2025-12-01', freq='MS'):
        days = exposure.observed_days(origin)
        rows.extend(dict(aircraft=ac, origin=str(origin.date()), observed_days=int(n),
                         available30=bool(n >= 30), available60=bool(n >= 60)) for ac, n in days.items())
    table = pd.DataFrame(rows)
    if not table.available30.equals(table.available60):
        raise RuntimeError('Separate A16 threshold-60 simulation required; do not assume equivalence')
    # When available, both use the identical increment/D; otherwise identical fallback.
    return table


def configuration():
    amendment = amendment006()
    coverage = threshold_equivalence()
    spec = dict(study='A16_corrected', amendment006=amendment, seed=20261112, seed_study=17,
        R=200, B=999, cells=core.cells(), variants=list(core.VARIANTS), minimum_days=30,
        sensitivity_minimum_days=60, sensitivity60_functionally_identical_on_all_origins=True,
        budget_A16_hours=60, budget_A9_hours=120, budget_prior=historical_budget(),
        historical=historical_hashes(), sources={name: sha(ROOT / name) for name in OP_SOURCES},
        old_scientific_configuration_sha256=sha(ROOT / 'data/derived/a16/power/configuration.json'),
        original_controls_reused=False, errata_results_used=False)
    config = freeze(OUT / 'configuration.json', spec)
    coverage.to_csv(OUT / 'threshold_equivalence.csv', index=False)
    if not (OUT / 'state.json').exists():
        atomic_json(OUT / 'state.json', dict(status='configuration_frozen', started_utc=core.utc_now(),
            completed_replicas=0, seed_study=17, configuration_sha256=config['configuration_sha256']))
    return config


def load_config():
    config = json.loads((OUT / 'configuration.json').read_text(encoding='utf-8'))
    if config['amendment006'] != amendment006() or config['seed_study'] != 17 or config['R'] != 200:
        raise RuntimeError('Corrected configuration mismatch')
    for name, digest in config['sources'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Corrected execution source changed: ' + name)
    return config


def integrity(config):
    load_config()
    check_historical(config['historical'])
    return dict(scientific_artifacts_unchanged=True, original_controls_preserved=True,
                seed_study=17, corrected_exposure=True)


def initializer(telemetry):
    global _DESIGN, _TELEMETRY
    truth, _, _, channels, _, _ = load_design()
    _DESIGN = (truth, channels)
    _TELEMETRY = telemetry


def worker(cell, replicate, destination):
    destination = Path(destination)
    started = time.perf_counter()
    incident_count = 0
    def heartbeat(variant, origin):
        nonlocal incident_count
        if _TELEMETRY:
            try:
                atomic_json(OUT / 'worker_status' / cell['id'] / f'{replicate:03d}.json',
                    dict(pid=os.getpid(), variant=variant, origin=origin, updated_utc=core.utc_now()))
            except OSError:
                incident_count += 1
    with patch.object(core, 'synthetic_inputs', synthetic_flow17), \
         patch.object(core, 'PilotEvaluation', CorrectedSharedTraining), \
         patch.object(core, 'atomic_json', atomic_json):
        record = core.execute_replica(cell, replicate, *_DESIGN, destination, heartbeat)
    runtime = dict(seconds=time.perf_counter() - started, pid=os.getpid(), seed_study=17,
                   telemetry_write_incidents=incident_count, finished_utc=core.utc_now())
    atomic_json(destination / 'runtime.json', runtime)
    return record, runtime


def snapshot(folder):
    return {p.name: sha(p) for p in sorted(folder.iterdir())
            if p.is_file() and p.name != 'runtime.json' and not p.name.endswith('.tmp')}


def verify(workers):
    config = configuration()
    integrity(config)
    cell = config['cells'][0]
    initializer(False)
    first = OUT / 'replicas' / cell['id'] / '000'
    before, _ = worker(cell, 0, str(first))
    if not all(v['status'] == 'ok' for v in before['variants'].values()):
        raise RuntimeError('Corrected synthetic replay failed')
    parallel.native_threads_one()
    second = OUT / 'reproducibility' / (cell['id'] + '_000')
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=initializer, initargs=(False,)) as pool:
        after, _ = pool.submit(worker, cell, 0, str(second)).result()
    if snapshot(first) != snapshot(second) or before != after:
        raise RuntimeError('Corrected A16 replay differs between serial and spawned execution')
    integrity(config)
    atomic_json(OUT / 'multicore_verification.json', dict(all_scientific_artifacts_byte_identical=True,
        parallel_workers=workers, complete_corrected_replays=2, replicated_index=0,
        duplicated_replay_not_counted_as_new=True, identical_artifacts=len(snapshot(first)),
        sha256=snapshot(first), configuration_sha256=config['configuration_sha256'],
        sources={name: sha(ROOT / name) for name in OP_SOURCES}))
    print('Corrected flow 17: two complete synthetic replays are byte-identical.', flush=True)


def report(state, frames):
    old = pd.read_csv(ROOT / 'data/derived/a16/power/summary.csv')
    old = old[old.estimand.isin(['aggregate', 'family'])]
    text = ('# T16 — A16 corrigida, fluxo 17\n\n'
        'Emenda 006 commitada em 6848e19. R=200, B=999, seis processos; orçamento '
        'A16 de 60 h com custos anteriores acumulados. Controles antigos estão '
        'invalidados pelo defeito para esta finalidade e não entram nas estimativas novas.\n\n'
        f'Estado: **{state["status"]}**. Réplicas novas concluídas: '
        f'{state.get("completed_replicas", 0)} de 1 800.\n\n'
        '## Controles antigos, preservados\n\n' + old[['cell', 'variant', 'estimand', 'frequency', 'failures']]
        .to_markdown(index=False, floatfmt='.5f') + '\n\n## Resultados corrigidos\n\n')
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        selected = combined[combined.estimand.isin(['aggregate', 'family'])]
        text += selected[['cell', 'variant', 'estimand', 'frequency', 'ci_lo', 'ci_hi', 'failures']].to_markdown(
            index=False, floatfmt='.5f') + '\n\n'
    else:
        text += 'Nenhuma célula nova completa; não interpretar frequências parciais.\n\n'
    text += ('Wilson 95% e erro Monte Carlo, falhas no denominador e limites '
        'alternativos em summary.csv. Limiar 60 dias é funcionalmente equivalente '
        'a 30 em todas as origens externas destes relógios; isso não vale '
        'automaticamente para A5 ou A9.\n\n')
    if state['status'] == 'stopped_type_I':
        text += '**Parada:** nova falha de calibração; não fazer outra correção ou iniciar A9/A10.\n'
    elif state['status'] == 'complete':
        text += ('A16 concluída. Para modos A4, poder ≥0,8 sugere pequeno valor '
            'preditivo da idade sob o gerador; <0,5 é inconclusivo; 0,5–0,8 é '
            'evidência fraca. Considerar intervalos e tamanho; FH realizadas '
            'continua hipótese gerada pelos dados. Próxima etapa: piloto A9/A10.\n')
    if state.get('error'):
        text += '\nErro de execução: ' + state['error_type'] + ': ' + state['error'] + '\n'
    (ROOT / 'analysis/a16_corrected_report.md').write_text(text, encoding='utf-8')
    budget_path = OUT / 'budget.json'
    if (budget_path.exists() and state['status'] == 'running'
            and state.get('completed_replicas', 0) % 10 != 0):
        return
    budget = load_config()['budget_prior']
    runtimes = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT / 'replicas').glob('*/*/runtime.json'))]
    seconds = sum(row['seconds'] for row in runtimes)
    atomic_json(budget_path, dict(prior=budget, new_recorded_worker_seconds=seconds,
        as_of_completed_replicas=state.get('completed_replicas', 0),
        cumulative_recorded_worker_seconds=budget['old_recorded_worker_seconds'] + budget['pilot_seconds'] + seconds,
        budget_hours=60, budget_exceeded_by_recorded_worker_sum=(
            budget['old_recorded_worker_seconds'] + budget['pilot_seconds'] + seconds > 60 * 3600),
        excess_does_not_trigger_optional_stopping=True))


def run(workers):
    load_config()
    with ExitStack() as stack:
        for obj, name, replacement in (
            (core, 'OUT', OUT), (core, 'atomic_json', atomic_json),
            (parallel, 'OUT', OUT), (parallel, 'OP_SOURCES', OP_SOURCES),
            (parallel, 'load_config', load_config), (parallel, 'integrity', integrity),
            (parallel, 'initializer', initializer), (parallel, 'worker', worker), (parallel, 'report', report)):
            stack.enter_context(patch.object(obj, name, replacement))
        return parallel.run(workers)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=6)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(args.workers)
    else:
        raise SystemExit(run(args.workers))
