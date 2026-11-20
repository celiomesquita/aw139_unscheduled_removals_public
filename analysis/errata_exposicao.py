"""T15: separate, reproducible A5/A4 implementation errata under amendment 006."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import io
import json
import multiprocessing
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd

from a5_validation import (VARIANTS as A5_VARIANTS, ADMIN_IDS, KEYS, bootstrap_decision, metrics)
from a4_validation import VARIANTS as A4_VARIANTS
from exposure_errata import CorrectedA4, CorrectedA5
from feasibility import ROOT, DERIVED, ANONYMISED, load_omth
from a16_generator import sha
from round5_execution import amendment006, atomic_json, check_historical, freeze, historical_hashes

CONFIG = DERIVED / 'exposure_errata_configuration.json'


class SharedThresholdTraining:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold_training = {}

    def prepare(self, origin, variant):
        key = (origin, variant)
        if key not in self.threshold_training:
            self.threshold_training[key] = super().prepare(origin, variant)
        return self.threshold_training[key]


class ErrataA5(SharedThresholdTraining, CorrectedA5):
    pass


class ErrataA4(SharedThresholdTraining, CorrectedA4):
    pass


def configuration():
    return freeze(CONFIG, dict(amendment006=amendment006(), seed=20261112, B=10000,
        thresholds=[30, 60], a5_variants=list(A5_VARIANTS), a4_variants=list(A4_VARIANTS),
        historical=historical_hashes(), sources={name: sha(ROOT / name) for name in
            ['analysis/errata_exposicao.py', 'analysis/exposure_errata.py', 'analysis/round5_execution.py',
             'analysis/emenda_A16_A9_007.md']}))


def inputs(model):
    spells = pd.read_csv(DERIVED / 'spells.csv', parse_dates=['att', 'rem'])
    flights = pd.read_csv(ANONYMISED / 'hours_flown.csv')
    removals = pd.read_csv(DERIVED / 'removals_clean.csv', parse_dates=['att', 'rem'])
    kept = pd.read_csv(DERIVED / 'k1_candidates.csv')
    candidates = sorted(kept.loc[kept.retained, 'pn'])
    admin = pd.read_csv(DERIVED / 'removal_label_audit.csv', parse_dates=['att', 'rem'])
    admin = admin[admin.audit_id.isin(ADMIN_IDS)]
    if len(admin) != 4:
        raise RuntimeError('Expected four administrative exclusions')
    args = (spells, flights, candidates, load_omth(),
            pd.read_csv(ROOT / 'config/rotor_inspection_map.csv'), removals, admin)
    if model == 'A5':
        return ErrataA5(*args)
    return ErrataA4(*args, domain=pd.read_csv(ROOT / 'config/a4_scale_map.csv'))


def output_folder(model, threshold):
    folder = DERIVED / (model.lower() + '_errata')
    return folder if threshold == 30 else folder / 'minimum_60_days'


def canonical(frame):
    return pd.read_csv(io.StringIO(frame.to_csv(index=False)), float_precision='round_trip')


def affected_counts(original, corrected):
    keys = ['spell_id', 'pn', 'aircraft', 'origin', 'horizon']
    old = original.set_index(keys).sort_index()
    new = corrected.set_index(keys).sort_index()
    if not old.index.equals(new.index):
        raise RuntimeError('Correction changed the prediction population')
    values = pd.DataFrame(index=old.index)
    for name in ('w_selected', 'e_selected', 'baseline'):
        values[name + '_changed'] = old[name].ne(new[name])
    probabilities = [name for name in old.columns if name in ('baseline', 'w_selected', 'e_selected')
                     or name in [f'{p}_{s}' for p in ('w', 'e') for s in ('FH', 'calendar', 'takeoffs')]]
    values['any_probability_changed'] = old[probabilities].ne(new[probabilities]).any(axis=1)
    values['fallback_marker_changed'] = old[['w_selected_fallback', 'e_selected_fallback']].ne(
        new[['w_selected_fallback', 'e_selected_fallback']]).any(axis=1)
    rows = []
    for pn in ('aggregate', *sorted(old.index.get_level_values('pn').unique())):
        group = values if pn == 'aggregate' else values[values.index.get_level_values('pn') == pn]
        rows.append(dict(pn=pn, predictions=len(group), **{column: int(group[column].sum()) for column in values}))
    return pd.DataFrame(rows)


def variant_job(job):
    model, variant = job
    engine = inputs(model)
    original_folder = DERIVED / model.lower()
    original = pd.read_csv(original_folder / f'predictions_{variant}.csv', float_precision='round_trip')
    shared_fits, shared_effects, shared_hyper = None, None, None
    for threshold in (30, 60):
        folder = output_folder(model, threshold)
        folder.mkdir(parents=True, exist_ok=True)
        engine.exposure.minimum_days = threshold
        selection_start = len(engine.selections)
        print(model, variant, 'threshold', threshold, flush=True)
        frame = engine.run_variant(variant)
        checked = canonical(frame)
        if variant == 'realized_fh':
            pd.testing.assert_frame_equal(checked, original, check_exact=True)
        frame.to_csv(folder / f'predictions_{variant}.csv', index=False)
        counts = affected_counts(original, checked)
        counts.to_csv(folder / f'affected_{variant}.csv', index=False)
        score, calibration = metrics(frame)
        if model == 'A4':
            score = score[score.model.isin(['w_selected', 'e_selected', 'baseline'])]
            calibration = calibration[calibration.model.isin(['w_selected', 'e_selected', 'baseline'])]
        for obj in (score, calibration):
            obj['variant'] = variant
        score.to_csv(folder / f'metrics_{variant}.csv', index=False)
        calibration.to_csv(folder / f'calibration_{variant}.csv', index=False)
        intervals, boots, decisions = [], [], []
        aggregations = ('aircraft', 'unit') if model == 'A4' and variant == 'principal' else ('aircraft',)
        criteria = ('K2',) if model == 'A5' else ('K2-A4', 'K2-idade')
        for aggregation in aggregations:
            for criterion in criteria:
                paired = frame.copy()
                if criterion == 'K2-idade':
                    paired['baseline'] = paired.e_selected
                outcome, ci, boot = bootstrap_decision(paired, engine.exposure.aircraft,
                    engine.candidates, reps=10000, aggregation=aggregation)
                for obj in (ci, boot):
                    obj['variant'], obj['aggregation'], obj['criterion'] = variant, aggregation, criterion
                intervals.append(ci)
                boots.append(boot.reset_index(names='replicate'))
                decisions.append(dict(variant=variant, aggregation=aggregation, criterion=criterion,
                    outcome=outcome, predictions=len(frame), risk_spells=frame.spell_id.nunique(),
                    aircraft=frame.aircraft.nunique()))
        pd.concat(intervals).to_csv(folder / f'intervals_{variant}.csv', index=False)
        pd.concat(boots).to_csv(folder / f'bootstrap_{variant}.csv', index=False)
        pd.DataFrame(decisions).to_csv(folder / f'decision_{variant}.csv', index=False)
        if threshold == 30:
            shared_fits = pd.DataFrame(engine.fits)
            if model == 'A4':
                shared_effects, shared_hyper = pd.DataFrame(engine.effects), pd.DataFrame(engine.hyper)
        shared_fits.to_csv(folder / f'fits_{variant}.csv', index=False)
        pd.DataFrame(engine.selections[selection_start:]).to_csv(folder / f'scale_selection_{variant}.csv', index=False)
        if model == 'A4':
            shared_effects.to_csv(folder / f'effects_{variant}.csv', index=False)
            shared_hyper.to_csv(folder / f'hyperparameters_{variant}.csv', index=False)
        groups = frame.groupby(['pn', 'aircraft', 'origin', 'horizon']).agg(
            risk_units=('spell_id', 'size'), observed=('y', 'sum'),
            hW_expected=('w_selected', 'sum'), hE_expected=('e_selected', 'sum'), baseline_expected=('baseline', 'sum'))
        groups.reset_index().to_csv(folder / f'counts_{variant}.csv', index=False)
    return dict(model=model, variant=variant, realized_fh_exact=variant == 'realized_fh')


def combine():
    comparison, decisions = [], []
    for model, variants in (('A5', A5_VARIANTS), ('A4', A4_VARIANTS)):
        original = DERIVED / model.lower()
        old_ci = pd.read_csv(original / ('k2_intervals.csv' if model == 'A5' else 'intervals.csv'),
                             float_precision='round_trip')
        old_decisions = pd.read_csv(original / 'decision.csv')
        if model == 'A5':
            old_ci['criterion'], old_ci['aggregation'] = 'K2', 'aircraft'
            old_decisions['criterion'], old_decisions['aggregation'] = 'K2', 'aircraft'
        for threshold in (30, 60):
            folder = output_folder(model, threshold)
            ci = pd.concat([pd.read_csv(folder / f'intervals_{v}.csv', float_precision='round_trip') for v in variants],
                           ignore_index=True)
            dec = pd.concat([pd.read_csv(folder / f'decision_{v}.csv') for v in variants], ignore_index=True)
            ci.to_csv(folder / 'intervals.csv', index=False)
            dec.to_csv(folder / 'decision.csv', index=False)
            for prefix in ('metrics', 'calibration', 'fits'):
                pd.concat([pd.read_csv(folder / f'{prefix}_{v}.csv', float_precision='round_trip') for v in variants], ignore_index=True).to_csv(
                    folder / (prefix + '.csv'), index=False)
            if model == 'A4':
                for prefix in ('effects', 'hyperparameters'):
                    pd.concat([pd.read_csv(folder / f'{prefix}_{v}.csv', float_precision='round_trip') for v in variants], ignore_index=True).to_csv(
                        folder / (prefix + '.csv'), index=False)
            else:
                pd.concat([pd.read_csv(folder / f'scale_selection_{v}.csv') for v in variants], ignore_index=True).to_csv(
                    folder / 'scale_selection.csv', index=False)
            keys = ['variant', 'aggregation', 'criterion']
            merged_decisions = old_decisions[keys + ['outcome']].merge(dec[keys + ['outcome']],
                on=keys, suffixes=('_original', '_corrected'), validate='one_to_one')
            merged_decisions['model'], merged_decisions['threshold'] = model, threshold
            decisions.append(merged_decisions)
            compared = old_ci.merge(ci, on=['pn', *keys], suffixes=('_original', '_corrected'), validate='one_to_one')
            changes = pd.concat([pd.read_csv(folder / f'affected_{v}.csv').assign(variant=v) for v in variants])
            compared = compared.merge(changes, on=['variant', 'pn'], validate='many_to_one')
            compared['model'], compared['threshold'] = model, threshold
            comparison.append(compared)
    compared, decisions = pd.concat(comparison, ignore_index=True), pd.concat(decisions, ignore_index=True)
    compared.to_csv(DERIVED / 'exposure_errata_comparison.csv', index=False)
    decisions.to_csv(DERIVED / 'exposure_errata_decisions.csv', index=False)
    principal = compared[compared.variant.eq('principal') & compared.aggregation.eq('aircraft') &
                         compared.pn.eq('aggregate')]
    report = ('# T15 — errata de implementação da exposição prevista\n\n'
        'Emenda 006 commitada em 6848e19. A5/A4 originais, relatórios, parâmetros '
        'do gerador e decisões pré-registradas permanecem preservados. As análises '
        'abaixo são correções de desvio de implementação, apresentadas ao lado das '
        'originais; não as substituem.\n\n'
        + decisions[decisions.variant.eq('principal') & decisions.aggregation.eq('aircraft')].to_markdown(index=False)
        + '\n\n' + principal[['model', 'threshold', 'criterion', 'delta_log_original', 'ci_lo_original',
            'ci_hi_original', 'delta_log_corrected', 'ci_lo_corrected', 'ci_hi_corrected',
            'w_selected_changed', 'e_selected_changed', 'any_probability_changed']].to_markdown(index=False, floatfmt='.8f')
        + '\n\nMesmas sementes e B=10 000; todas as variantes originais e limiar '
        'principal 30 dias, com sensibilidade 60 dias. realized_fh reproduziu '
        'integralmente as previsões originais em A5 e A4, nos dois limiares. '
        'exposure_errata_comparison.csv contém valores originais/corrigidos e '
        'contagens afetadas para agregado e cada P/N, inclusive sensibilidades. '
        'Mudanças em probabilidades são separadas de mudanças em marcadores; '
        'novas colunas de cobertura não são contadas como mudança preditiva.\n\n'
        'Nenhum resultado da errata é usado para modificar A16/A9, parâmetros '
        'verdadeiros ou seleção dos 11 P/N. O manuscrito não foi editado por esta execução.\n')
    (ROOT / 'analysis/errata_exposicao_report.md').write_text(report, encoding='utf-8')


def snapshots():
    paths = [p for model in ('A5', 'A4') for p in (DERIVED / (model.lower() + '_errata')).rglob('*.csv')]
    paths += [DERIVED / 'exposure_errata_comparison.csv', DERIVED / 'exposure_errata_decisions.csv',
              ROOT / 'analysis/errata_exposicao_report.md']
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def main(workers=2):
    config = configuration()
    atomic_json(DERIVED / 'exposure_errata_state.json', dict(status='running', pid=os.getpid(), full_runs=0,
        configuration_sha256=config['configuration_sha256']))
    jobs = [('A5', variant) for variant in A5_VARIANTS] + [('A4', variant) for variant in A4_VARIANTS]
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    initial = None
    for run in (1, 2):
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
            list(pool.map(variant_job, jobs, chunksize=1))
        combine()
        current = snapshots()
        if initial is None:
            initial = current
        elif initial != current:
            raise RuntimeError('Two complete implementation-errata runs differ')
        check_historical(config['historical'])
        atomic_json(DERIVED / 'exposure_errata_state.json', dict(status='running' if run == 1 else 'complete',
            full_runs=run, last_run_seconds=time.perf_counter() - started,
            configuration_sha256=config['configuration_sha256'], original_artifacts_unchanged=True))
    atomic_json(DERIVED / 'exposure_errata_verification.json', dict(full_runs=2,
        identical_artifacts=len(initial), sha256=initial, original_artifacts_unchanged=True,
        realized_fh_exact=True, amendment006=config['amendment006']))
    print('T15 complete: original artifacts preserved; two full runs identical.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    main(args.workers)
