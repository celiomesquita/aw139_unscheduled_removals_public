"""Complete five-replica A9/A10 timing pilot; never launches the main experiment."""
import os

for _variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_variable] = '1'

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import time
import traceback

import pandas as pd
import psutil

from a16_generator import ROOT, load_design, sha
from a9_simulation import run_replica
from a9_warmup import SharedWarmup, materialise, verify_configuration
from round5_execution import atomic_json, check_historical, freeze

OUT = ROOT / 'data/derived/a9/pilot'
PILOT_CELL = dict(index=71, level='amplified', knowledge='realized_fh', r=10, scenario='B-gradual')


def utc():
    return datetime.now(timezone.utc).isoformat()


def runtime_sources():
    paths = sorted((ROOT / 'analysis').glob('a9_*.py'))
    paths += [ROOT / 'analysis' / name for name in ('a16_generator.py', 'a4_models.py',
        'a4_validation.py', 'a5_models.py', 'a5_validation.py', 'exposure_errata.py',
        'round5_execution.py', 'emenda_A16_A9_010.md', 'emenda_A16_A9_011.md')]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def prepare():
    warmup = verify_configuration()
    check_historical(warmup['historical'])
    previous = json.loads((ROOT / 'data/derived/a16/flow17/state.json').read_text())
    if previous['status'] != 'complete' or not previous['null_controls_passed']:
        raise RuntimeError('A16 corrected null controls have not passed')
    proof_path = ROOT / 'data/derived/a9/integration_verification.json'
    proof = json.loads(proof_path.read_text())
    if proof['failures'] or proof['errors'] or not proof['two_complete_artificial_runs_identical']:
        raise RuntimeError('A9 integration verification did not pass')
    sources = runtime_sources()
    if sources != proof['sources']:
        raise RuntimeError('Runtime sources differ from the verified integration')
    inputs = ['data/anonymised/hours_flown.csv', 'data/derived/stoppages.csv',
              'config/a4_scale_map.csv', 'data/derived/a9/resources/preventive_mh.csv',
              'data/derived/a9/resources/manifest.json', 'data/derived/a9/warmup/configuration.json',
              'data/derived/a16/flow17/state.json', 'data/derived/a16/flow17/summary.csv']
    specification = dict(pilot_cell=PILOT_CELL, pilot_replicates=5, policies=6,
        budget_hours=120, main_cells=72, minimum_R=200, maximum_R=1000,
        reserve_factor=1.5, main_executed=False, pilot_in_inference=False,
        effects_saved_or_inspected=False, seed_study=9, warmup_study=90, phase='pilot',
        sources=sources, inputs={p: sha(ROOT / p) for p in inputs},
        integration_verification_sha256=sha(proof_path), historical=warmup['historical'],
        versions={name: importlib.metadata.version(name) for name in ('numpy', 'pandas', 'scipy', 'mip', 'psutil')})
    OUT.mkdir(parents=True, exist_ok=True)
    return freeze(OUT / 'configuration.json', specification)


def integrity(configuration, historical=False):
    if runtime_sources() != configuration['sources']:
        raise RuntimeError('A9 runtime source changed during pilot')
    for name, digest in configuration['inputs'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('A9 input changed during pilot: ' + name)
    if historical:
        check_historical(configuration['historical'])


def report(state, timings, manifest=None):
    lines = ['# A9/A10 — piloto completo de tempo e memória', '',
        'Cinco réplicas excluídas da inferência, célula 71, seis políticas em cada réplica.',
        'Emendas 010/011 fixadas antes de observações avaliadas.', '',
        f"Estado: **{state['status']}**. Réplicas completas: {len(timings)}/5.", '',
        'Nenhuma tabela de custo, ganho ou alarme do piloto é salva ou inspecionada.',
        'R permanece indefinido até cinco réplicas completas e verificação de orçamento.', '']
    if manifest:
        lines += [f"Maior tempo completo: {manifest['worst_replica_seconds']:.3f} s.",
            f"R bruto pela fórmula: {manifest['raw_R']}; R fixado: {manifest['fixed_R']}.",
            f"Orçamento de 120 h comporta R≥200: {manifest['budget_passed']}.", '',
            'Se o mínimo não couber, a execução principal permanece parada, sem reduzir a grade.', '']
    if state.get('error_type'):
        lines += [f"Falha computacional: {state['error_type']}. Não substituir a réplica por outra semente.", '']
    (ROOT / 'analysis/a9_pilot_report.md').write_text('\n'.join(lines), encoding='utf-8')


def run():
    configuration = prepare()
    integrity(configuration, historical=True)
    lock = OUT / 'run.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('A9 pilot lock exists; inspect its PID before resuming')
    os.write(descriptor, str(os.getpid()).encode())
    os.close(descriptor)
    started = time.perf_counter()
    state = dict(status='running', pid=os.getpid(), started_utc=utc(),
        configuration_sha256=configuration['configuration_sha256'], pilot_replicates=0,
        pilot_started=True, main_replicas=0, main_executed=False, R=None)
    timings = []
    def update(**fields):
        state.update(fields, updated_utc=utc(), elapsed_seconds=time.perf_counter() - started)
        atomic_json(OUT / 'state.json', state)
        central = json.loads((ROOT / 'data/derived/a9/state.json').read_text())
        central.update(status='pilot_' + state['status'], pilot_started=True,
            pilot_replicas=len(timings), main_replicas=0, R=state.get('R'),
            pilot_pid=state['pid'], pilot_stage=state.get('stage'),
            pilot_policy=state.get('policy'), pilot_month=state.get('month'),
            pilot_pn=state.get('pn'), pilot_updated_utc=state['updated_utc'])
        atomic_json(ROOT / 'data/derived/a9/state.json', central)
    try:
        update(stage='loading_design')
        report(state, timings)
        truth, _, _, channels, _, _ = load_design()
        domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
        flights = pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv')
        stoppages = pd.read_csv(ROOT / 'data/derived/stoppages.csv')
        resources = pd.read_csv(ROOT / 'data/derived/a9/resources/preventive_mh.csv').set_index('pn').principal_mh.to_dict()
        for replicate in range(5):
            checkpoint = OUT / f'replica_{replicate:02d}.json'
            if checkpoint.exists():
                previous = json.loads(checkpoint.read_text())
                if (previous.get('status') != 'complete' or previous.get('complete_policies') != 6 or
                        previous.get('configuration_sha256') != configuration['configuration_sha256']):
                    raise RuntimeError('Preserved failed pilot replica cannot be replaced')
                timings.append(previous)
                continue
            update(replicate=replicate, stage='warmup', policy=None, month=None, pn=None)
            tick = time.perf_counter()
            folder = materialise(replicate, PILOT_CELL['level'], 'pilot')
            shared = SharedWarmup(folder)
            def heartbeat(**fields):
                integrity(configuration)
                update(**fields)
                print(json.dumps(dict(replicate=replicate, **fields)), flush=True)
            result = run_replica(PILOT_CELL, replicate, 'pilot', shared, truth, channels,
                                 domain, flights, stoppages, resources, heartbeat)
            if len(result['policies']) != 6:
                raise RuntimeError('Pilot did not complete all six policies')
            seconds = time.perf_counter() - tick
            memory = psutil.Process().memory_info()
            # Deliberately discard all financial/detection outputs before checkpointing.
            del result
            record = dict(replicate=replicate, status='complete', seconds=seconds,
                process_peak_bytes=int(getattr(memory, 'peak_wset', memory.rss)), complete_policies=6,
                configuration_sha256=configuration['configuration_sha256'], effects_saved=False)
            atomic_json(checkpoint, record)
            timings.append(record)
            integrity(configuration, historical=True)
            update(pilot_replicates=len(timings), stage='replica_complete')
            report(state, timings)
        maximum = max(row['seconds'] for row in timings)
        raw = 50 * math.floor(120 * 3600 / (72 * 1.5 * maximum) / 50)
        passed = raw >= 200
        manifest = dict(pilot_replicates=5, budget_hours=120, main_cells=72,
            worst_replica_seconds=maximum, raw_R=raw, fixed_R=min(raw, 1000) if passed else None,
            budget_passed=passed, minimum_R=200, reserve_factor=1.5,
            effects_saved_or_inspected=False, pilot_in_inference=False, main_executed=False,
            configuration_sha256=configuration['configuration_sha256'])
        atomic_json(OUT / 'manifest.json', manifest)
        update(status='complete' if passed else 'stopped_budget', finished_utc=utc(),
               R=manifest['fixed_R'], stage='finished', pilot_replicates=5)
        report(state, timings, manifest)
        return 0 if passed else 2
    except Exception as exc:
        atomic_json(OUT / 'failure.json', dict(error_type=type(exc).__name__, error=str(exc),
                                              traceback=traceback.format_exc(), state=state))
        if 'replicate' in state:
            checkpoint = OUT / f"replica_{state['replicate']:02d}.json"
            if not checkpoint.exists():
                atomic_json(checkpoint, dict(replicate=state['replicate'], status='failed',
                    error_type=type(exc).__name__, configuration_sha256=configuration['configuration_sha256']))
        update(status='stopped_implementation', finished_utc=utc(), error_type=type(exc).__name__)
        report(state, timings)
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    arguments = parser.parse_args()
    if arguments.run:
        raise SystemExit(run())
    if arguments.prepare:
        print(prepare()['configuration_sha256'])
