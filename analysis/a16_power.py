"""Checkpointed A16 execution under the committed 60-hour amendment."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
from statistics import NormalDist
import subprocess
import time
import traceback

import numpy as np
import pandas as pd
import psutil
import scipy

from a15_stability import protected_hashes
from a16_generator import ROOT, OUT as GENERATOR, committed_protocol, load_design, sha
from a16_pilot import PilotEvaluation, synthetic_inputs
from a5_validation import KEYS, bootstrap_decision, metrics

OUT = ROOT / 'data/derived/a16/power'
VARIANTS = ('principal', 'realized_fh')
LEVELS = ('calibrated', 'null', 'amplified')
COPIES = (1, 2, 4)
SOURCES = ('analysis/a16_power.py', 'analysis/a16_pilot.py', 'analysis/a16_generator.py',
           'analysis/a4_validation.py', 'analysis/a4_models.py', 'analysis/a5_validation.py',
           'analysis/a5_models.py', 'analysis/emenda_A16_A9_004.md')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def cells():
    grid = [dict(id=f'{level}_x{copies}', level=level, copies=copies,
                 seed_cell=3 * LEVELS.index(level) + COPIES.index(copies))
            for level in LEVELS for copies in COPIES]
    return sorted(grid, key=lambda cell: (cell['level'] != 'null',
                  LEVELS.index(cell['level']), cell['copies']))


def committed_amendment():
    path = 'analysis/emenda_A16_A9_003.md'
    revision = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', path],
                                       cwd=ROOT, text=True).strip()
    original = subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)
    actual = (ROOT / path).read_bytes()
    if original.replace(b'\r\n', b'\n') != actual.replace(b'\r\n', b'\n'):
        raise ValueError('Budget amendment is not the committed version')
    if '**60 h**' not in actual.decode('utf-8-sig'):
        raise ValueError('Expected committed 60-hour A16 budget')
    return revision, sha(ROOT / path)


def build_config():
    revision, protocol_hash = committed_protocol()
    amendment_revision, amendment_hash = committed_amendment()
    pilot = json.loads((ROOT / 'data/derived/a16/pilot_manifest.json').read_text(encoding='utf-8'))
    verification = json.loads((ROOT / 'data/derived/a16/verification.json').read_text(encoding='utf-8'))
    generator = json.loads((GENERATOR / 'manifest.json').read_text(encoding='utf-8'))
    if not generator['gate_passed'] or verification['full_generator_runs'] != 2:
        raise ValueError('Validated and reproduced generator required')
    if pilot['pilot_in_results'] or pilot['effects_inspected']:
        raise ValueError('Pilot cannot supply primary results')
    if pilot['protocol_sha256'] != protocol_hash:
        raise ValueError('Protocol changed after pilot')
    raw_r = 50 * math.floor(60 * 3600 / (9 * 1.5 * pilot['worst_replica_seconds']) / 50)
    if raw_r < 200:
        raise ValueError('Amended budget still cannot accommodate minimum R')
    fixed_r = min(raw_r, 1000)
    protected = protected_hashes()
    protected['analysis/preregistro_A16_A9.md'] = protocol_hash
    if protected != generator['protected']:
        raise ValueError('Protected real-data artifacts changed')
    for name, digest in generator['inputs'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Validated generator input changed: ' + name)
    config = dict(study='A16', protocol_revision=revision, protocol_sha256=protocol_hash,
        budget_amendment_revision=amendment_revision, budget_amendment_sha256=amendment_hash,
        budget_A16_hours=60, budget_A9_hours=120, total_T12_hours=180,
        pilot_worst_seconds=pilot['worst_replica_seconds'], R=fixed_r, B=999,
        cells=cells(), variants=list(VARIANTS), seed=20261112, seed_study=16,
        seed_axes=['seed', 'study', 'cell', 'replicate', 'PN', 'aircraft', 'channel', 'copy', 'risk'],
        error_type_I_stop_threshold=.10, pilot_in_results=False,
        pilot_manifest_sha256=sha(ROOT / 'data/derived/a16/pilot_manifest.json'),
        generator_manifest_sha256=sha(GENERATOR / 'manifest.json'),
        sources={name: sha(ROOT / name) for name in SOURCES}, protected=protected,
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      scipy=scipy.__version__, psutil=psutil.__version__))
    config['configuration_sha256'] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return config


def freeze_config():
    config = build_config()
    path = OUT / 'configuration.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != config:
            raise ValueError('Frozen A16 configuration differs; do not overwrite or resume with changed code')
    else:
        atomic_json(path, config)
    return config


def write_gzip_csv(frame, path):
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as stream:
                frame.to_csv(stream, index=False)


def rejected(ci):
    indexed = ci.set_index('pn')
    aggregate = bool(indexed.at['aggregate', 'ci_lo'] > 0)
    by_pn = {pn: bool(row.simultaneous_lo > 0) for pn, row in indexed.iterrows() if pn != 'aggregate'}
    return dict(aggregate_rejected=aggregate, family_rejected=any(by_pn.values()), pn_rejected=by_pn,
                delta_log=float(indexed.at['aggregate', 'delta_log']))


def execute_replica(cell, replicate, truth, channels, destination, heartbeat=None):
    """Same A4 forecasts/metrics/bootstrap, with synthetic input and B=999."""
    destination.mkdir(parents=True, exist_ok=True)
    results = {}
    engine = None
    try:
        spells, flights, incomplete = synthetic_inputs(replicate, truth, channels,
            copies=cell['copies'], level=cell['level'], seed_study=16, seed_cell=cell['seed_cell'])
        domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
        removals = pd.DataFrame(columns=['Attached Part #', 'Attached Serial #', 'Aircraft #', 'rem'])
        admin = pd.DataFrame(columns=KEYS)
        tasks = pd.DataFrame(columns=['Aircraft #', 'Task #', 'd'])
        mapping = pd.read_csv(ROOT / 'config/rotor_inspection_map.csv')
        engine = PilotEvaluation(spells, flights, domain.pn.tolist(), tasks, mapping, removals, admin, domain=domain)
        for variant in VARIANTS:
            try:
                frames = []
                for origin in pd.date_range('2025-01-01', '2025-12-01', freq='MS'):
                    if heartbeat:
                        heartbeat(variant, str(origin.date()))
                    frame = engine.forecast(origin, variant)
                    if len(frame):
                        frames.append(engine.select(frame, [], variant, origin))
                if not frames:
                    raise ValueError('No eligible predictions in synthetic replica')
                predictions = pd.concat(frames, ignore_index=True)
                write_gzip_csv(predictions, destination / f'predictions_{variant}.csv.gz')
                score, calibration = metrics(predictions)
                score[score.model.isin(['w_selected', 'e_selected', 'baseline'])].to_csv(
                    destination / f'metrics_{variant}.csv', index=False)
                calibration[calibration.model.isin(['w_selected', 'e_selected', 'baseline'])].to_csv(
                    destination / f'calibration_{variant}.csv', index=False)
                intervals = []
                criteria = {}
                for criterion in ('K2-A4', 'K2-idade'):
                    paired = predictions.copy()
                    if criterion == 'K2-idade':
                        paired['baseline'] = paired.e_selected
                    outcome, ci, _ = bootstrap_decision(paired, engine.exposure.aircraft, engine.candidates, reps=999)
                    if not np.isfinite(ci[['delta_log', 'ci_lo', 'ci_hi', 'simultaneous_lo', 'simultaneous_hi']]).all().all():
                        raise ValueError('Nonfinite confidence interval')
                    criteria[criterion] = dict(outcome=outcome, **rejected(ci))
                    ci['criterion'] = criterion
                    intervals.append(ci)
                pd.concat(intervals).to_csv(destination / f'intervals_{variant}.csv', index=False)
                results[variant] = dict(status='ok', predictions=len(predictions),
                    risk_spells=int(predictions.spell_id.nunique()), aircraft=int(predictions.aircraft.nunique()),
                    hW_fallback=float(predictions.w_selected_fallback.mean()),
                    hE_fallback=float(predictions.e_selected_fallback.mean()), criteria=criteria)
            except Exception as error:
                results[variant] = dict(status='failed', error_type=type(error).__name__, error=str(error))
        pd.DataFrame(engine.effects).to_csv(destination / 'shared_training_effects.csv', index=False)
        pd.DataFrame(engine.hyper).to_csv(destination / 'shared_training_hyperparameters.csv', index=False)
        pd.DataFrame(engine.fits).to_csv(destination / 'individual_reference_fits.csv', index=False)
        generated = dict(synthetic_spells=len(spells), incomplete_fragments_excluded=incomplete)
    except Exception as error:
        results = {variant: dict(status='failed', error_type=type(error).__name__, error=str(error)) for variant in VARIANTS}
        generated = {}
    summary = dict(cell=cell['id'], level=cell['level'], copies=cell['copies'],
                   replicate=replicate, variants=results, **generated)
    summary['artifacts'] = {p.name: sha(p) for p in sorted(destination.iterdir())
                            if p.is_file() and not p.name.endswith('.tmp')
                            and p.name not in ('summary.json', 'runtime.json')}
    atomic_json(destination / 'summary.json', summary)
    return summary


def wilson(successes, n):
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError('Invalid binomial counts')
    z = NormalDist().inv_cdf(.975)
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0., center - half), min(1., center + half)


def summarize_cell(cell, summaries, candidates, expected_r):
    if len(summaries) != expected_r or sorted(s['replicate'] for s in summaries) != list(range(expected_r)):
        raise ValueError('Cell cannot be evaluated before all fixed replicas are final')
    rows = []
    for variant in VARIANTS:
        successful = [s['variants'][variant] for s in summaries if s['variants'][variant]['status'] == 'ok']
        failures = expected_r - len(successful)
        for estimand in ('aggregate', 'family', *candidates):
            decisions = [s['criteria']['K2-idade'] for s in successful]
            positives = sum(d['aggregate_rejected'] if estimand == 'aggregate' else
                            d['family_rejected'] if estimand == 'family' else d['pn_rejected'][estimand]
                            for d in decisions)
            low, high = wilson(positives, expected_r)
            p = positives / expected_r
            rows.append(dict(cell=cell['id'], level=cell['level'], copies=cell['copies'], variant=variant,
                estimand=estimand, metric='type_I' if cell['level'] == 'null' else 'power',
                detections=int(positives), R=expected_r, successes=len(successful), failures=failures,
                frequency=p, ci_lo=low, ci_hi=high, mc_se=math.sqrt(p * (1 - p) / expected_r),
                failure_lower=p, failure_upper=(positives + failures) / expected_r))
    return pd.DataFrame(rows)


def calibration_failure(summary):
    if not summary.level.eq('null').all():
        return False
    aggregate = summary[summary.estimand.isin(['aggregate', 'family'])]
    return bool((aggregate.successes.eq(0) | aggregate.frequency.gt(.10)).any())


def check_sources(config):
    for name, digest in config['sources'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Source changed during A16: ' + name)
    if committed_protocol()[1] != config['protocol_sha256'] or committed_amendment()[1] != config['budget_amendment_sha256']:
        raise RuntimeError('Committed scientific protocol changed during A16')


def write_report(state, aggregate):
    report = ('# A16 — execução principal\n\n'
        'Pré-registro aa129e2, emenda de orçamento 003 commitada em 9c1a0ee. '
        'A16: 60 h; A9/A10: 120 h; R=200 por célula, B=999, nove células e duas '
        'variantes. O piloto de cinco réplicas continua excluído.\n\n'
        f'Estado: **{state["status"]}**. Réplicas principais concluídas: '
        f'{state.get("completed_replicas", 0)} de 1 800. '
        'Células nulas ×1, ×2 e ×4 precedem as células de efeito. Frequências '
        'parciais não acionam a parada.\n\n')
    if len(aggregate):
        view = aggregate[aggregate.estimand.isin(['aggregate', 'family'])]
        report += (view[['cell', 'variant', 'estimand', 'frequency', 'ci_lo', 'ci_hi', 'failures']]
                   .to_markdown(index=False, floatfmt='.5f') + '\n\n'
                   'Wilson 95%, unidade: réplica. Falhas permanecem no denominador '
                   'como não detecção; limites alternativos e resultados por P/N '
                   'constam de summary.csv. Todas as linhas acima correspondem '
                   'a células completas, com 200 réplicas.\n\n')
    if state['status'] == 'stopped_type_I':
        report += ('**Parada pré-registrada:** erro tipo I agregado/familiar acima de '
                   '0,10 ou controle não avaliável. Não interpretar poder ou iniciar A9/A10.\n')
    elif state['status'] == 'complete':
        report += ('A16 concluída. A interpretação dos modos A4 é condicional ao '
                   'gerador: ≥0,8, nulo real sugere pequeno valor preditivo; <0,5, '
                   'inconclusivo; 0,5–0,8, evidência fraca. Intervalos que cruzam '
                   'limiares limitam a classificação. FH realizadas continua hipótese '
                   'gerada pelos dados. Próxima etapa de T12: piloto A9/A10.\n')
    else:
        report += 'Ainda não há conclusão sobre informatividade do nulo ou ganho de política.\n'
    if state.get('error'):
        report += '\nErro de execução: ' + state['error_type'] + ': ' + state['error'] + '\n'
    (ROOT / 'analysis/a16_power_report.md').write_text(report, encoding='utf-8')


def acquire_lock():
    path = OUT / 'run.lock'
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        if psutil.pid_exists(previous['pid']):
            process = psutil.Process(previous['pid'])
            if abs(process.create_time() - previous['process_created']) < 1:
                raise RuntimeError('A16 process is already running')
        path.replace(OUT / ('run.stale.' + str(time.time_ns()) + '.json'))
    with path.open('x', encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(), process_created=psutil.Process().create_time(), started_utc=utc_now()), stream)
    return path


def run():
    config = freeze_config()
    lock = acquire_lock()
    state = dict(status='running', started_utc=utc_now(), pid=os.getpid(), completed_replicas=0,
                 configuration_sha256=config['configuration_sha256'], R=config['R'], budget_hours=60)
    aggregate_frames = []
    decisions = []
    try:
        truth, _, _, channels, _, _ = load_design()
        candidates = sorted(truth.pn)
        for cell in config['cells']:
            check_sources(config)
            summaries = []
            for replicate in range(config['R']):
                destination = OUT / 'replicas' / cell['id'] / f'{replicate:03d}'
                final = destination / 'summary.json'
                if final.exists():
                    record = json.loads(final.read_text(encoding='utf-8'))
                    if record['cell'] != cell['id'] or record['replicate'] != replicate:
                        raise RuntimeError('Checkpoint identity mismatch')
                    for name, digest in record['artifacts'].items():
                        if sha(destination / name) != digest:
                            raise RuntimeError('Checkpoint artifact changed: ' + str(destination / name))
                else:
                    check_sources(config)
                    def heartbeat(variant, origin):
                        state.update(cell=cell['id'], replicate=replicate, variant=variant,
                                     origin=origin, updated_utc=utc_now())
                        atomic_json(OUT / 'state.json', state)
                    started = time.perf_counter()
                    record = execute_replica(cell, replicate, truth, channels, destination, heartbeat)
                    memory = psutil.Process().memory_info()
                    atomic_json(destination / 'runtime.json', dict(seconds=time.perf_counter() - started,
                        finished_utc=utc_now(), peak_process_bytes=int(getattr(memory, 'peak_wset', memory.rss))))
                summaries.append(record)
                for variant, result in record['variants'].items():
                    age = result.get('criteria', {}).get('K2-idade', {})
                    decisions.append(dict(cell=cell['id'], replicate=replicate, variant=variant,
                        status=result['status'], aggregate_rejected=age.get('aggregate_rejected'),
                        family_rejected=age.get('family_rejected'), outcome=age.get('outcome'),
                        pn_rejected=';'.join(sorted(pn for pn, hit in age.get('pn_rejected', {}).items() if hit)),
                        hW_fallback=result.get('hW_fallback'), hE_fallback=result.get('hE_fallback'),
                        error_type=result.get('error_type', ''), error=result.get('error', '')))
                state['completed_replicas'] += 1
                state['updated_utc'] = utc_now()
                atomic_json(OUT / 'state.json', state)
                print('Completed', cell['id'], replicate + 1, '/', config['R'], flush=True)
                if state['completed_replicas'] == 1 or state['completed_replicas'] % 10 == 0:
                    write_report(state, pd.concat(aggregate_frames, ignore_index=True)
                                 if aggregate_frames else pd.DataFrame())
            summary = summarize_cell(cell, summaries, candidates, config['R'])
            aggregate_frames.append(summary)
            combined = pd.concat(aggregate_frames, ignore_index=True)
            combined.to_csv(OUT / 'summary.csv', index=False)
            pd.DataFrame(decisions).to_csv(OUT / 'replicate_decisions.csv', index=False)
            current = protected_hashes()
            current['analysis/preregistro_A16_A9.md'] = committed_protocol()[1]
            if current != config['protected']:
                raise RuntimeError('Protected A4/A5 artifacts changed')
            if calibration_failure(summary):
                state.update(status='stopped_type_I', stopped_cell=cell['id'], finished_utc=utc_now())
                atomic_json(OUT / 'state.json', state)
                write_report(state, combined)
                return 2
            state['completed_cells'] = [f['cell'].iloc[0] for f in aggregate_frames]
            write_report(state, combined)
        state.update(status='complete', finished_utc=utc_now(), protected_files_unchanged=True,
                     null_controls_passed=True, a9_executed=False)
        atomic_json(OUT / 'state.json', state)
        write_report(state, pd.concat(aggregate_frames, ignore_index=True))
        return 0
    except Exception as error:
        state.update(status='execution_error', error_type=type(error).__name__, error=str(error), updated_utc=utc_now())
        atomic_json(OUT / 'state.json', state)
        write_report(state, pd.concat(aggregate_frames, ignore_index=True) if aggregate_frames else pd.DataFrame())
        traceback.print_exc()
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        config = freeze_config()
        write_report(dict(status='configuration_frozen', completed_replicas=0), pd.DataFrame())
        print('Frozen A16 configuration:', config['configuration_sha256'], 'R =', config['R'])
    else:
        raise SystemExit(run())
