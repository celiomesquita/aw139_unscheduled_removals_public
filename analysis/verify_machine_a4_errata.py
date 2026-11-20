"""T17 author closure: isolated, unchanged T15 A4 estimators; two full local replays.

Never run in the reference checkout. No A5 refit, A9 policy or optimisation.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
from pathlib import Path
import time
import traceback

import pandas as pd
import psutil

from a4_validation import VARIANTS
from a5_validation import bootstrap_decision, metrics
from errata_exposicao import inputs, canonical
from machine_reproduction import compare_author_closure_csv_bytes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/derived/machine_transfer/a4_errata_linux'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(proof):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'verification.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    temporary.replace(target)


def job(spec):
    """Same A4 calculation as T15 variant_job, without its Windows-only guard.

    Outputs go to a new verification directory. Old-host checking is performed
    by the coordinator with T17d, never by modifying an estimation function.
    """
    run, variant = spec
    started, cpu = time.perf_counter(), time.process_time()
    engine = inputs('A4')
    shared = None
    for threshold in (30, 60):
        folder = OUT / f'run{run}' / f'minimum_{threshold}_days'
        folder.mkdir(parents=True, exist_ok=True)
        engine.exposure.minimum_days = threshold
        selection_start = len(engine.selections)
        frame = engine.run_variant(variant)
        frame.to_csv(folder / f'predictions_{variant}.csv', index=False)
        score, calibration = metrics(frame)
        score = score[score.model.isin(['w_selected', 'e_selected', 'baseline'])]
        calibration = calibration[calibration.model.isin(['w_selected', 'e_selected', 'baseline'])]
        for table in (score, calibration):
            table['variant'] = variant
        score.to_csv(folder / f'metrics_{variant}.csv', index=False)
        calibration.to_csv(folder / f'calibration_{variant}.csv', index=False)
        intervals, boots, decisions = [], [], []
        for aggregation in (('aircraft', 'unit') if variant == 'principal' else ('aircraft',)):
            for criterion in ('K2-A4', 'K2-idade'):
                paired = frame.copy()
                if criterion == 'K2-idade':
                    paired['baseline'] = paired.e_selected
                outcome, ci, boot = bootstrap_decision(paired, engine.exposure.aircraft,
                    engine.candidates, reps=10000, aggregation=aggregation)
                for table in (ci, boot):
                    table['variant'], table['aggregation'], table['criterion'] = variant, aggregation, criterion
                intervals.append(ci)
                boots.append(boot.reset_index(names='replicate'))
                decisions.append(dict(variant=variant, aggregation=aggregation, criterion=criterion,
                    outcome=outcome, predictions=len(frame), risk_spells=frame.spell_id.nunique(),
                    aircraft=frame.aircraft.nunique()))
        pd.concat(intervals).to_csv(folder / f'intervals_{variant}.csv', index=False)
        pd.concat(boots).to_csv(folder / f'bootstrap_{variant}.csv', index=False)
        pd.DataFrame(decisions).to_csv(folder / f'decision_{variant}.csv', index=False)
        if threshold == 30:
            shared = {'fits': pd.DataFrame(engine.fits), 'effects': pd.DataFrame(engine.effects),
                      'hyperparameters': pd.DataFrame(engine.hyper)}
        for prefix, table in shared.items():
            table.to_csv(folder / f'{prefix}_{variant}.csv', index=False)
        pd.DataFrame(engine.selections[selection_start:]).to_csv(
            folder / f'scale_selection_{variant}.csv', index=False)
        groups = frame.groupby(['pn', 'aircraft', 'origin', 'horizon']).agg(
            risk_units=('spell_id', 'size'), observed=('y', 'sum'),
            hW_expected=('w_selected', 'sum'), hE_expected=('e_selected', 'sum'),
            baseline_expected=('baseline', 'sum'))
        groups.reset_index().to_csv(folder / f'counts_{variant}.csv', index=False)
    return dict(run=run, variant=variant, wall_seconds=time.perf_counter() - started,
                cpu_seconds=time.process_time() - cpu, rss_bytes_at_end=psutil.Process().memory_info().rss)


def compare_variant(variant, reference, proof, margins, objectives, diagnostic_changes):
    for threshold in (30, 60):
        new = OUT / 'run1' / f'minimum_{threshold}_days'
        old = reference / 'data/derived/a4_errata'
        if threshold == 60:
            old = old / 'minimum_60_days'
        for path in sorted(new.glob(f'*_{variant}.csv')):
            baseline = old / path.name
            key = f'minimum_{threshold}_days/' + path.name
            report = {}
            proof['columns'][key] = report
            actual_bytes, old_bytes = path.read_bytes(), baseline.read_bytes()
            compare_author_closure_csv_bytes(actual_bytes, old_bytes, path.name, report)
            if path.name.startswith('hyperparameters_'):
                new_h = pd.read_csv(path, float_precision='round_trip')
                old_h = pd.read_csv(baseline, float_precision='round_trip')
                for current, historical in zip(new_h.to_dict('records'), old_h.to_dict('records')):
                    a, b = current.get('objective'), historical.get('objective')
                    defined = pd.notna(a) and pd.notna(b)
                    for field in ('converged','attempts','successful_attempts','evaluations','boundary','zero_variance'):
                        av, bv = current.get(field), historical.get(field)
                        if not ((pd.isna(av) and pd.isna(bv)) or av == bv):
                            diagnostic_changes.append(dict(threshold=threshold, variant=variant, origin=current['origin'],
                                model=current['model'], field=field, historical=bv, current=av, blocking=False))
                    objectives.append(dict(threshold=threshold, variant=variant,
                        origin=current['origin'], model=current['model'],
                        historical_objective=b, current_objective=a,
                        signed_displacement=a-b if defined else None,
                        absolute_displacement=abs(a-b) if defined else None,
                        relative_displacement=abs(a-b)/abs(b) if defined and b != 0 else (0. if defined and a == b else None),
                        historical_objective_zero=bool(defined and b == 0),
                        historical_successful_attempts=historical.get('successful_attempts'),
                        current_successful_attempts=current.get('successful_attempts'),
                        historical_evaluations=historical.get('evaluations'),
                        current_evaluations=current.get('evaluations')))
                pd.DataFrame(objectives).sort_values(['threshold','variant','origin','model']).to_csv(
                    OUT / 'objective_displacements.csv', index=False)
            if diagnostic_changes:
                pd.DataFrame(diagnostic_changes).sort_values(['threshold','variant','origin','model','field']).to_csv(
                    OUT / 'optimizer_diagnostic_changes.csv', index=False)
            save(proof)
        new_ci = pd.read_csv(new / f'intervals_{variant}.csv', float_precision='round_trip')
        old_ci = pd.read_csv(old / f'intervals_{variant}.csv', float_precision='round_trip')
        for current, historical in zip(new_ci.to_dict('records'), old_ci.to_dict('records')):
            for field in ('ci_lo', 'simultaneous_lo'):
                a, b = current[field], historical[field]
                margin = abs(b)
                margins.append(dict(threshold=threshold, variant=variant,
                    aggregation=current['aggregation'], criterion=current['criterion'], pn=current['pn'],
                    field=field, historical=b, current=a, signed_displacement=a-b,
                    absolute_displacement=abs(a-b), historical_distance_to_zero=margin,
                    fraction_of_historical_margin=abs(a-b)/margin if margin else 0.,
                    displacement_towards_zero=abs(a)<abs(b)))
        # Explicit Bonferroni sets, not just numerical closeness of endpoints.
        keys = ['variant', 'aggregation', 'criterion']
        for label, group in new_ci.groupby(keys, sort=True):
            select = old_ci
            for key, value in zip(keys, label):
                select = select[select[key].eq(value)]
            passed = lambda x: sorted(x.loc[x.pn.ne('aggregate') & x.simultaneous_lo.gt(0), 'pn'])
            if passed(group) != passed(select):
                raise AssertionError('Bonferroni PN set changed')


def snapshot(run):
    return {str(p.relative_to(OUT / f'run{run}')): sha(p)
            for p in sorted((OUT / f'run{run}').rglob('*.csv'))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    if ROOT == args.reference.resolve() or ROOT.is_relative_to(args.reference.resolve()):
        raise RuntimeError('A4 transfer verification requires an isolated checkout')
    if not 1 <= args.workers <= 6:
        raise ValueError('At most six workers + coordinator + resource tracker = eight processes')
    proof = dict(status='running', workers=args.workers, variants=list(VARIANTS), thresholds=[30, 60],
        B=10000, full_runs=0, columns={}, timings=[], historical_outputs_modified=False,
        estimators_unchanged=True, affected_count_tables='not used: these diagnose errata versus original, not transfer',
        same_host_bitwise=False, author_closure=True,
        blocking_rules=['scientific_decision','interval_sign','local_byte_identity'])
    margins, objectives, diagnostic_changes = [], [], []
    started = time.perf_counter()
    save(proof)
    pool = None
    try:
        for run in (1, 2):
            pool = ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn'))
            pending = {pool.submit(job, (run, variant)): variant for variant in VARIANTS}
            for future in as_completed(pending):
                result = future.result()
                proof['timings'].append(result)
                variant = pending[future]
                if run == 1:
                    compare_variant(variant, args.reference, proof, margins, objectives, diagnostic_changes)
                    pd.DataFrame(margins).sort_values(['threshold','variant','aggregation','criterion','pn','field']).to_csv(
                        OUT / 'interval_margin_displacements.csv', index=False)
                else:
                    for threshold in (30, 60):
                        first = OUT / 'run1' / f'minimum_{threshold}_days'
                        second = OUT / 'run2' / f'minimum_{threshold}_days'
                        for p in first.glob(f'*_{variant}.csv'):
                            if sha(p) != sha(second / p.name):
                                raise AssertionError('Two local A4 outputs differ: ' + p.name)
                save(proof)
            pool.shutdown(wait=True)
            pool = None
            proof['full_runs'] = run
        if snapshot(1) != snapshot(2):
            raise AssertionError('Two complete local A4 runs differ')
        proof.update(status='passed', same_host_bitwise=True, sha256=snapshot(1),
                     bonferroni_sets_equal=True, outcomes_and_signs_equal=True)
    except Exception as error:
        if pool is not None:
            pool.terminate_workers()
        proof.update(status='STOP', error_type=type(error).__name__, error=str(error))
        traceback.print_exc()
    finally:
        proof['verification_wall_seconds'] = time.perf_counter() - started
        save(proof)
    return 0 if proof['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
