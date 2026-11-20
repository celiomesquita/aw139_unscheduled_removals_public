"""Parallelize independent A16 replicas while preserving the frozen science."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import json
import multiprocessing
import os
from pathlib import Path
import time

import pandas as pd
import psutil

import a16_power as core
from a16_generator import load_design, sha
from a15_stability import protected_hashes

OUT = core.OUT
MANUSCRIPT = 'paper/manuscript.tex'
OP_SOURCES = ('analysis/a16_multicore.py', 'analysis/emenda_A16_A9_005.md')
_DESIGN = None
_HEARTBEATS = False


def native_threads_one():
    # Set before spawn: numpy is imported afresh in each child process.
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'


def load_config():
    config = json.loads((OUT / 'configuration.json').read_text(encoding='utf-8'))
    if config['R'] != 200 or config['B'] != 999 or config['budget_A16_hours'] != 60:
        raise RuntimeError('Unexpected frozen scientific configuration')
    core.check_sources(config)
    return config


def integrity(config):
    core.check_sources(config)
    actual = protected_hashes()
    actual['analysis/preregistro_A16_A9.md'] = core.committed_protocol()[1]
    for name, digest in config['protected'].items():
        if name != MANUSCRIPT and actual.get(name) != digest:
            raise RuntimeError('Scientific artifact changed: ' + name)
    generator = json.loads((core.GENERATOR / 'manifest.json').read_text(encoding='utf-8'))
    for name, digest in generator['inputs'].items():
        if sha(core.ROOT / name) != digest:
            raise RuntimeError('Generator input changed: ' + name)
    return dict(scientific_artifacts_unchanged=True,
        manuscript_original_sha256=config['protected'][MANUSCRIPT],
        manuscript_current_sha256=actual[MANUSCRIPT],
        manuscript_changed_externally=actual[MANUSCRIPT] != config['protected'][MANUSCRIPT])


def initializer(heartbeats):
    global _DESIGN, _HEARTBEATS
    truth, _, _, channels, _, _ = load_design()
    _DESIGN = (truth, channels)
    _HEARTBEATS = heartbeats


def worker(cell, replicate, destination):
    destination = Path(destination)
    started = time.perf_counter()
    pid = os.getpid()
    def heartbeat(variant, origin):
        if _HEARTBEATS:
            core.atomic_json(OUT / 'worker_status' / cell['id'] / f'{replicate:03d}.json',
                dict(status='running', pid=pid, cell=cell['id'], replicate=replicate,
                     variant=variant, origin=origin, updated_utc=core.utc_now()))
    record = core.execute_replica(cell, replicate, *_DESIGN, destination, heartbeat)
    runtime = dict(seconds=time.perf_counter() - started, pid=pid, native_threads=1,
                   finished_utc=core.utc_now(), peak_process_bytes=psutil.Process().memory_info().rss)
    core.atomic_json(destination / 'runtime.json', runtime)
    if _HEARTBEATS:
        core.atomic_json(OUT / 'worker_status' / cell['id'] / f'{replicate:03d}.json',
            dict(status='completed', pid=pid, cell=cell['id'], replicate=replicate,
                 updated_utc=core.utc_now()))
    return record, runtime


def scientific_snapshot(folder):
    return {p.name: sha(p) for p in sorted(folder.iterdir())
            if p.is_file() and p.name != 'runtime.json' and not p.name.endswith('.tmp')}


def verify(workers):
    config = load_config()
    before = integrity(config)
    cell = next(c for c in config['cells'] if c['id'] == 'null_x4')
    references = []
    for replicate in range(workers):
        folder = OUT / 'replicas' / cell['id'] / f'{replicate:03d}'
        record = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
        if not all(v['status'] == 'ok' for v in record['variants'].values()):
            raise RuntimeError('Verification reference did not finish successfully')
        references.append((folder, scientific_snapshot(folder),
            json.loads((folder / 'runtime.json').read_text(encoding='utf-8'))['seconds']))
    native_threads_one()
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=initializer, initargs=(False,)) as pool:
        jobs = {pool.submit(worker, cell, r, str(OUT / 'multicore_verification' / f'{r:03d}')): r
                for r in range(workers)}
        durations, pids = [], []
        for future, r in jobs.items():
            _, runtime = future.result()
            destination = OUT / 'multicore_verification' / f'{r:03d}'
            if scientific_snapshot(destination) != references[r][1]:
                raise RuntimeError('Multicore/native-thread results differ from serial reference: ' + str(r))
            durations.append(runtime['seconds'])
            pids.append(runtime['pid'])
    elapsed = time.perf_counter() - started
    if integrity(config) != before:
        raise RuntimeError('Artifacts changed during parallel verification')
    proof = dict(original_configuration_sha256=config['configuration_sha256'],
        parallel_workers=workers, distinct_processes=len(set(pids)), native_threads=1,
        replicas=[dict(cell=cell['id'], replicate=r) for r in range(workers)],
        all_scientific_artifacts_byte_identical=True,
        archived_serial_seconds=sum(row[2] for row in references),
        parallel_wall_seconds=elapsed, worker_seconds=durations,
        observed_speedup=sum(row[2] for row in references) / elapsed,
        timing_comparison='Archived sequential timings versus simultaneous replay, including spawn overhead',
        completed_utc=core.utc_now(), integrity=before,
        sources={name: sha(core.ROOT / name) for name in OP_SOURCES})
    core.atomic_json(OUT / 'multicore_verification.json', proof)
    print(json.dumps({k: proof[k] for k in ('parallel_workers', 'distinct_processes',
        'all_scientific_artifacts_byte_identical', 'archived_serial_seconds',
        'parallel_wall_seconds', 'observed_speedup')}, indent=2), flush=True)


def checkpoint(cell, replicate):
    folder = OUT / 'replicas' / cell['id'] / f'{replicate:03d}'
    final = folder / 'summary.json'
    if not final.exists():
        return None
    record = json.loads(final.read_text(encoding='utf-8'))
    if record['cell'] != cell['id'] or record['replicate'] != replicate:
        raise RuntimeError('Checkpoint identity mismatch')
    for name, digest in record['artifacts'].items():
        if sha(folder / name) != digest:
            raise RuntimeError('Completed checkpoint changed: ' + str(folder / name))
    return record


def decision_rows(records):
    rows = []
    for record in records:
        for variant, result in record['variants'].items():
            age = result.get('criteria', {}).get('K2-idade', {})
            rows.append(dict(cell=record['cell'], replicate=record['replicate'], variant=variant,
                status=result['status'], aggregate_rejected=age.get('aggregate_rejected'),
                family_rejected=age.get('family_rejected'), outcome=age.get('outcome'),
                pn_rejected=';'.join(sorted(pn for pn, hit in age.get('pn_rejected', {}).items() if hit)),
                hW_fallback=result.get('hW_fallback'), hE_fallback=result.get('hE_fallback'),
                error_type=result.get('error_type', ''), error=result.get('error', '')))
    return rows


def report(state, frames):
    core.write_report(state, pd.concat(frames, ignore_index=True) if frames else pd.DataFrame())
    path = core.ROOT / 'analysis/a16_power_report.md'
    text = path.read_text(encoding='utf-8')
    text += ('\nExecução multicore: ' + str(state['workers']) +
             ' processos, um thread numérico por processo. Configuração científica '
             'original preservada; reproduções paralelas não contam como réplicas adicionais.\n')
    if state.get('manuscript_changed_externally'):
        text += ('\nAlteração editorial externa no manuscrito registrada separadamente; '
                 'os artefatos científicos A4/A5 e pré-registros permanecem protegidos.\n')
    path.write_text(text, encoding='utf-8')


def run(workers):
    config = load_config()
    proof = json.loads((OUT / 'multicore_verification.json').read_text(encoding='utf-8'))
    op_sources = {name: sha(core.ROOT / name) for name in OP_SOURCES}
    if (not proof['all_scientific_artifacts_byte_identical'] or proof['sources'] != op_sources
            or proof['parallel_workers'] != workers):
        raise RuntimeError('Matching successful multicore verification required')
    previous = json.loads((OUT / 'state.json').read_text(encoding='utf-8'))
    if previous['status'] == 'stopped_type_I':
        raise RuntimeError('Cannot resume through a preregistered calibration stop')
    lock = core.acquire_lock()
    current_integrity = integrity(config)
    preserved = {str(p.relative_to(OUT)): sha(p) for p in sorted((OUT / 'replicas').glob('*/*/summary.json'))}
    manifest = dict(original_configuration_sha256=config['configuration_sha256'],
        workers=workers, native_threads=1, sources=op_sources, scientific_configuration_changed=False,
        integrity=current_integrity, preserved_completed_checkpoints=preserved,
        preserved_count=len(preserved), previous_state=previous, started_utc=core.utc_now(),
        verification_sha256=sha(OUT / 'multicore_verification.json'))
    core.atomic_json(OUT / 'multicore_execution.json', manifest)
    state = dict(status='running', started_utc=manifest['started_utc'],
        original_started_utc=previous.get('original_started_utc', previous['started_utc']),
        pid=os.getpid(), workers=workers, native_threads=1, execution_mode='multicore',
        configuration_sha256=config['configuration_sha256'], R=config['R'], budget_hours=60,
        completed_replicas=0, preserved_replicas=len(preserved), **current_integrity)
    frames, all_records = [], []
    pool = None
    try:
        native_threads_one()
        truth, _, _, _, _, _ = load_design()
        candidates = sorted(truth.pn)
        for cell in config['cells']:
            integrity(config)
            if {name: sha(core.ROOT / name) for name in OP_SOURCES} != op_sources:
                raise RuntimeError('Multicore execution source changed')
            records = {r: record for r in range(config['R']) if (record := checkpoint(cell, r)) is not None}
            pending = iter(r for r in range(config['R']) if r not in records)
            state.update(cell=cell['id'], completed_replicas=len(all_records) + len(records),
                         updated_utc=core.utc_now())
            core.atomic_json(OUT / 'state.json', state)
            if len(records) != config['R']:
                if pool is None:
                    pool = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'),
                                               initializer=initializer, initargs=(True,))
                active = {}
                def fill():
                    while len(active) < workers:
                        r = next(pending, None)
                        if r is None:
                            break
                        destination = OUT / 'replicas' / cell['id'] / f'{r:03d}'
                        active[pool.submit(worker, cell, r, str(destination))] = r
                fill()
                while active:
                    done, _ = wait(active, timeout=2, return_when=FIRST_COMPLETED)
                    for future in done:
                        r = active.pop(future)
                        record, runtime = future.result()
                        records[r] = record
                        print('Completed', cell['id'], r + 1, 'worker', runtime['pid'], flush=True)
                    fill()
                    state.update(completed_replicas=len(all_records) + len(records),
                                 active_replicas=sorted(active.values()), updated_utc=core.utc_now())
                    core.atomic_json(OUT / 'state.json', state)
                    if done:
                        report(state, frames)
            ordered = [records[r] for r in range(config['R'])]
            summary = core.summarize_cell(cell, ordered, candidates, config['R'])
            frames.append(summary)
            all_records.extend(ordered)
            combined = pd.concat(frames, ignore_index=True)
            combined.to_csv(OUT / 'summary.csv', index=False)
            pd.DataFrame(decision_rows(all_records)).to_csv(OUT / 'replicate_decisions.csv', index=False)
            state.update(**integrity(config), completed_cells=[f['cell'].iloc[0] for f in frames],
                         completed_replicas=len(all_records), active_replicas=[])
            if core.calibration_failure(summary):
                state.update(status='stopped_type_I', stopped_cell=cell['id'], finished_utc=core.utc_now())
                core.atomic_json(OUT / 'state.json', state)
                report(state, frames)
                return 2
            core.atomic_json(OUT / 'state.json', state)
            report(state, frames)
        state.update(status='complete', finished_utc=core.utc_now(), null_controls_passed=True, a9_executed=False)
        core.atomic_json(OUT / 'state.json', state)
        report(state, frames)
        return 0
    except Exception as error:
        state.update(status='execution_error', error_type=type(error).__name__, error=str(error),
                     updated_utc=core.utc_now())
        core.atomic_json(OUT / 'state.json', state)
        report(state, frames)
        raise
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=6)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--verify', action='store_true')
    action.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.workers <= psutil.cpu_count(logical=False):
        parser.error('Workers must be between one and the number of physical cores')
    if args.verify:
        verify(args.workers)
    else:
        raise SystemExit(run(args.workers))
