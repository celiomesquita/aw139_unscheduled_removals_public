"""T13: post-hoc diagnosis of frozen A16 predictions; no model fitting."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path

import numpy as np
import pandas as pd

from a15_stability import protected_hashes
from a5_models import Exposure, END
from a5_validation import bootstrap_decision, cluster_means, log_score

ROOT = Path(__file__).resolve().parent.parent
POWER = ROOT / 'data/derived/a16/power'
OUT = ROOT / 'data/derived/a16/null_diagnosis'
COLS = ['pn', 'aircraft', 'origin', 'horizon', 'y', 'w_selected', 'e_selected']
VARIANTS = ('principal', 'realized_fh')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def saved_inputs():
    paths = [p for p in (POWER / 'replicas').glob('*/*/*') if p.is_file() and not p.name.endswith('.tmp')]
    paths += [POWER / 'configuration.json', POWER / 'summary.csv', POWER / 'state.json',
              ROOT / 'data/anonymised/hours_flown.csv', ROOT / 'config/a4_scale_map.csv',
              ROOT / 'data/derived/a4/predictions_principal.csv']
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def focus_mask(frame):
    return frame.aircraft.str.split('-R').str[0].eq('AC-22') & frame.origin.eq('2025-12-01')


def contributions(frame):
    delta = log_score(frame.y, frame.w_selected) - log_score(frame.y, frame.e_selected)
    work = frame[['pn', 'aircraft', 'origin', 'horizon']].copy()
    work['delta'] = delta
    grouped = work.groupby(['pn', 'aircraft', 'origin', 'horizon']).delta.mean()
    grouped = grouped.groupby(level=['pn', 'aircraft', 'origin']).mean().reset_index()
    pieces = []
    pn_rows = []
    for pn, group in grouped.groupby('pn', sort=True):
        group = group.copy()
        n_aircraft = group.aircraft.nunique()
        n_origins = group.groupby('aircraft').origin.transform('size')
        group['contribution'] = group.delta / (n_aircraft * n_origins)
        pieces.extend(group[['pn', 'aircraft', 'origin', 'delta', 'contribution']].itertuples(index=False, name=None))
        point = float(cluster_means(frame[frame.pn.eq(pn)], delta[frame.pn.eq(pn)]).mean())
        np.testing.assert_allclose(group.contribution.sum(), point, rtol=0, atol=1e-14)
        pn_rows.append(dict(pn=pn, delta_log=point))
    aggregate = work.groupby(['aircraft', 'origin', 'horizon']).delta.mean()
    aggregate = aggregate.groupby(level=['aircraft', 'origin']).mean().reset_index()
    aggregate['contribution'] = aggregate.delta / (
        aggregate.aircraft.nunique() * aggregate.groupby('aircraft').origin.transform('size'))
    point = float(cluster_means(frame, delta).mean())
    np.testing.assert_allclose(aggregate.contribution.sum(), point, rtol=0, atol=1e-14)
    return pn_rows, pieces, list(aggregate.itertuples(index=False, name=None)), point


def diagnose_job(job):
    cell, copies, replicate, variant, candidates, aircraft = job
    folder = POWER / 'replicas' / cell / f'{replicate:03d}'
    original = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))['variants'][variant]
    tag = dict(cell=cell, copies=copies, replicate=replicate, variant=variant)
    if original['status'] != 'ok':
        # Preserve the historical failure; no new estimate replaces it.
        return dict(tag=tag, status='original_failed', failure_code=original['error_type'])
    frame = pd.read_csv(folder / f'predictions_{variant}.csv.gz', usecols=COLS, float_precision='round_trip')
    pn_rows, detail, aggregate_detail, point = contributions(frame)
    original_ci = pd.read_csv(folder / f'intervals_{variant}.csv', float_precision='round_trip')
    original_ci = original_ci[original_ci.criterion.eq('K2-idade')].drop(columns='criterion')
    np.testing.assert_allclose(point, original_ci.loc[original_ci.pn.eq('aggregate'), 'delta_log'].iloc[0],
                               rtol=0, atol=1e-14)
    paired = frame.assign(baseline=frame.e_selected)
    omitted = focus_mask(frame)
    diagnostic_outcome, exclusion_ci, _ = bootstrap_decision(paired[~omitted], aircraft, candidates, reps=999)
    aggregate_row = exclusion_ci[exclusion_ci.pn.eq('aggregate')].iloc[0]
    result = dict(tag=tag, status='ok', pn_rows=pn_rows, details=detail, aggregate_details=aggregate_detail,
        original_delta=point, original_aggregate_lo=float(original_ci.loc[original_ci.pn.eq('aggregate'), 'ci_lo'].iloc[0]),
        original_aggregate_hi=float(original_ci.loc[original_ci.pn.eq('aggregate'), 'ci_hi'].iloc[0]),
        excluded_rows=int(omitted.sum()), remaining_rows=int((~omitted).sum()),
        diagnostic_outcome=diagnostic_outcome,
        exclusion_ci=exclusion_ci.to_dict(orient='records'),
        excluded_delta=float(aggregate_row.delta_log), excluded_ci_lo=float(aggregate_row.ci_lo),
        excluded_ci_hi=float(aggregate_row.ci_hi))
    focus = frame[omitted & frame.pn.eq('3G3240V01731')]
    result['focus_probabilities'] = [dict(horizon=int(h), n=len(g), observed=float(g.y.mean()),
        hW=float(g.w_selected.mean()), hE=float(g.e_selected.mean())) for h, g in focus.groupby('horizon')]
    if cell == 'null_x4' and replicate < 20:
        outcome999, ci999, _ = bootstrap_decision(paired, aircraft, candidates, reps=999)
        columns = ['delta_log', 'ci_lo', 'ci_hi', 'simultaneous_lo', 'simultaneous_hi', 'missing_replicates']
        np.testing.assert_array_equal(ci999.set_index('pn')[columns].loc[original_ci.pn],
                                      original_ci.set_index('pn')[columns])
        outcome10000, ci10000, _ = bootstrap_decision(paired, aircraft, candidates, reps=10000)
        result['bootstrap_comparison'] = [dict(pn=a.pn, delta_log=float(a.delta_log),
            lo999=float(a.ci_lo), hi999=float(a.ci_hi), lo10000=float(b.ci_lo), hi10000=float(b.ci_hi),
            simultaneous_lo999=float(a.simultaneous_lo), simultaneous_lo10000=float(b.simultaneous_lo),
            aggregate_reject999=bool(a.ci_lo > 0) if a.pn == 'aggregate' else False,
            aggregate_reject10000=bool(b.ci_lo > 0) if b.pn == 'aggregate' else False,
            pn_reject999=bool(a.simultaneous_lo > 0) if a.pn != 'aggregate' else False,
            pn_reject10000=bool(b.simultaneous_lo > 0) if b.pn != 'aggregate' else False,
            outcome999=outcome999, outcome10000=outcome10000)
            for a, b in zip(ci999.itertuples(), ci10000.itertuples())]
    return result


def inventory():
    flights = pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv')
    exposure = Exposure(flights)
    clock = exposure.clocks(END + pd.Timedelta(days=1))
    bounds = exposure.flights.groupby('Aircraft #').d.agg(['min', 'max'])
    predictions = pd.read_csv(ROOT / 'data/derived/a4/predictions_principal.csv',
        usecols=['aircraft', 'origin', 'horizon', 'spell_id', 'w_selected_scale'])
    risk = predictions[predictions.horizon.eq(1)].groupby(['aircraft', 'origin']).spell_id.nunique()
    fh_risk = predictions[predictions.horizon.eq(1) & predictions.w_selected_scale.eq('FH')].groupby(
        ['aircraft', 'origin']).spell_id.nunique()
    rows, horizons = [], []
    for origin in pd.date_range('2025-01-01', '2025-12-01', freq='MS'):
        start = origin - pd.Timedelta(days=90)
        rates = {field: exposure.rates(clock, origin, field) for field in ('Hours', 'cycles')}
        for aircraft, b in bounds.iterrows():
            days = max(0, min(90, (origin - max(start, b['min'])).days))
            row = dict(aircraft=aircraft, origin=str(origin.date()), window_start=str(start.date()),
                window_end_exclusive=str(origin.date()), first_record=str(b['min'].date()),
                last_record=str(b['max'].date()), observed_days=days, incomplete_window=days < 90,
                risk_units=int(risk.get((aircraft, str(origin.date())), 0)),
                FH_risk_units=int(fh_risk.get((aircraft, str(origin.date())), 0)),
                coverage_kind='no_prior_records' if days == 0 else 'partial_positive' if days < 90 else 'complete',
                has_record_after_origin=bool(b['max'] >= origin),
                legacy_rate_FH=float(rates['Hours'][aircraft]), legacy_rate_takeoffs=float(rates['cycles'][aircraft]))
            rows.append(row)
            for horizon in (1, 2, 3):
                end = origin + pd.DateOffset(months=horizon)
                dates = pd.date_range(origin, end - pd.Timedelta(days=1))
                real_fh = float(clock['daily']['Hours'].loc[dates, aircraft].sum())
                expected = float(rates['Hours'][aircraft]) * len(dates)
                horizons.append(dict(aircraft=aircraft, origin=str(origin.date()), horizon=horizon,
                    target_last_day=str(dates[-1].date()), last_record=str(b['max'].date()),
                    extends_after_last_record=bool(dates[-1] > b['max']),
                    origin_after_last_record=bool(origin > b['max']), risk_units=row['risk_units'],
                    legacy_predicted_FH=expected, recorded_future_FH=real_fh,
                    predicted_realized_ratio=expected / real_fh if real_fh > 0 else np.nan))
    return pd.DataFrame(rows), pd.DataFrame(horizons)


def aggregate_contributions(accumulator, tag, rows, columns):
    for row in rows:
        labels = row[:columns]
        values = row[columns:]
        key = (tag['cell'], tag['variant'], *labels)
        entry = accumulator.setdefault(key, [0, np.zeros(len(values)), np.zeros(len(values))])
        array = np.array(values, dtype=float)
        entry[0] += 1
        entry[1] += array
        entry[2] += array * array


def contribution_table(accumulator, label_names, value_names):
    rows = []
    for key, (n, sums, squares) in sorted(accumulator.items()):
        row = dict(zip(['cell', 'variant', *label_names], key))
        row['replicas_present'] = n
        for i, name in enumerate(value_names):
            row[name + '_mean'] = float(sums[i] / n)
            row[name + '_sd'] = float(np.sqrt(max(0, (squares[i] - sums[i] ** 2 / n) / (n - 1)))) if n > 1 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def main(workers=6):
    before = protected_hashes()
    before.pop('paper/manuscript.tex')  # Concurrent editorial work is outside this diagnostic.
    inputs = saved_inputs()
    config = json.loads((POWER / 'configuration.json').read_text(encoding='utf-8'))
    candidates = sorted(pd.read_csv(ROOT / 'config/a4_scale_map.csv').pn)
    flights = pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv', usecols=['Aircraft #'])
    aircraft_base = sorted(flights['Aircraft #'].dropna().unique())
    jobs = []
    for cell in config['cells']:
        if cell['level'] != 'null':
            continue
        aircraft = sorted(f'{ac}-R{copy + 1:02d}' for ac in aircraft_base for copy in range(cell['copies']))
        jobs.extend((cell['id'], cell['copies'], r, v, candidates, aircraft) for r in range(200) for v in VARIANTS)
    OUT.mkdir(parents=True, exist_ok=True)
    per_pn, replicas, excluded_intervals, comparisons, focus_rows, failures = [], [], [], [], [], []
    detail_acc, aggregate_acc = {}, {}
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        for index, result in enumerate(pool.map(diagnose_job, jobs, chunksize=1)):
            tag = result['tag']
            if result['status'] != 'ok':
                failures.append(dict(**tag, status=result['status'], failure_code=result['failure_code']))
                continue
            per_pn.extend(dict(**tag, **row) for row in result['pn_rows'])
            replicas.append(dict(**tag, **{k: result[k] for k in ('original_delta', 'original_aggregate_lo', 'original_aggregate_hi',
                'excluded_rows', 'remaining_rows', 'diagnostic_outcome', 'excluded_delta', 'excluded_ci_lo', 'excluded_ci_hi')}))
            excluded_intervals.extend(dict(**tag, **row) for row in result['exclusion_ci'])
            comparisons.extend(dict(**tag, **row) for row in result.get('bootstrap_comparison', []))
            focus_rows.extend(dict(**tag, **row) for row in result['focus_probabilities'])
            aggregate_contributions(detail_acc, tag, result['details'], 3)
            aggregate_contributions(aggregate_acc, tag, result['aggregate_details'], 2)
            if (index + 1) % 100 == 0:
                print('Diagnosed', index + 1, '/', len(jobs), flush=True)
    tables = dict(pn_deltas=pd.DataFrame(per_pn), replica_exclusion=pd.DataFrame(replicas),
        exclusion_intervals=pd.DataFrame(excluded_intervals), bootstrap_comparison=pd.DataFrame(comparisons),
        focus_probabilities=pd.DataFrame(focus_rows), original_failures=pd.DataFrame(failures),
        pn_aircraft_origin=contribution_table(detail_acc, ['pn', 'aircraft', 'origin'], ['delta', 'contribution']),
        aggregate_aircraft_origin=contribution_table(aggregate_acc, ['aircraft', 'origin'], ['delta', 'contribution']))
    windows, horizons = inventory()
    tables.update(window_inventory=windows, incomplete_windows=windows[windows.incomplete_window],
        horizon_inventory=horizons, horizons_after_last_record=horizons[horizons.extends_after_last_record])
    for name, frame in tables.items():
        frame.to_csv(OUT / (name + '.csv'), index=False)
    render(tables)
    after = protected_hashes()
    after.pop('paper/manuscript.tex')
    if before != after or inputs != saved_inputs():
        raise RuntimeError('Original scientific artifacts changed during diagnosis')
    manifest = dict(diagnostic_only=True, models_fitted=0, original_barrier_replaced=False,
        original_failed_variants=len(failures), successful_variants=len(replicas),
        inputs=inputs, protected=before, script_sha256=sha(Path(__file__)),
        report_sha256=sha(ROOT / 'analysis/a16_null_diagnosis.md'),
        outputs={p.name: sha(p) for p in sorted(OUT.glob('*.csv'))})
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def render(tables):
    replicas = tables['replica_exclusion']
    replicas['bootstrap_se'] = (replicas.original_aggregate_hi - replicas.original_aggregate_lo) / 3.92
    aggregate = replicas.groupby(['cell', 'variant']).agg(
        n=('replicate', 'size'), original_mean=('original_delta', 'mean'),
        empirical_sd=('original_delta', 'std'), bootstrap_se_mean=('bootstrap_se', 'mean'),
        excluded_mean=('excluded_delta', 'mean'),
        original_positive_lo=('original_aggregate_lo', lambda s: int(s.gt(0).sum())),
        diagnostic_positive_lo=('excluded_ci_lo', lambda s: int(s.gt(0).sum())),
        excluded_rows=('excluded_rows', 'sum')).reset_index()
    pn = tables['pn_deltas'].groupby(['cell', 'variant', 'pn']).delta_log.agg(['mean', 'std', 'count']).reset_index()
    pn.to_csv(OUT / 'pn_summary.csv', index=False)
    focus = tables['focus_probabilities'].groupby(['cell', 'variant', 'horizon'])[
        ['observed', 'hW', 'hE']].mean().reset_index()
    comparison = tables['bootstrap_comparison']
    aggregate_boot = comparison[comparison.pn.eq('aggregate')].groupby('variant').agg(
        n=('replicate', 'size'), reject999=('aggregate_reject999', 'sum'),
        reject10000=('aggregate_reject10000', 'sum'),
        changed=('aggregate_reject999', 'size')).reset_index()
    aggregate_boot['changed'] = [int((g.aggregate_reject999 != g.aggregate_reject10000).sum())
        for _, g in comparison[comparison.pn.eq('aggregate')].groupby('variant')]
    affected = tables['incomplete_windows']
    observed = affected[affected.FH_risk_units.gt(0) & affected.observed_days.gt(0)]
    detail = tables['pn_aircraft_origin']
    focus_contribution = detail[detail.pn.eq('3G3240V01731') & detail.origin.eq('2025-12-01') &
        detail.aircraft.str.split('-R').str[0].eq('AC-22')].groupby(['cell', 'variant'])[
        ['delta_mean', 'contribution_mean']].mean().reset_index()
    focus_inventory = tables['horizon_inventory'][tables['horizon_inventory'].aircraft.eq('AC-22') &
        tables['horizon_inventory'].origin.eq('2025-12-01')]
    report = ('# T13 — diagnóstico dos controles nulos de A16\n\n'
        'Análise exploratória posterior à parada, usando somente artefatos salvos e '
        'relógios registrados. Nenhum modelo foi ajustado e nenhuma previsão foi corrigida. '
        'A decisão original de parada e os 600 controles permanecem preservados; '
        'a exclusão abaixo é diagnóstico, sem regra de decisão substituta.\n\n'
        '## Agregado original e exclusão AC-22/2025-12-01\n\n'
        + aggregate.to_markdown(index=False, floatfmt='.8f') + '\n\n'
        'Mesma agregação aeronave → origem → horizonte e bootstrap PCG64/20261112, '
        'B=999, universo original de 24/48/96 códigos e Bonferroni para 11 P/N. '
        'Excluem-se todas as linhas AC-22/2025-12-01 e suas cópias, mantendo '
        'o universo de reamostragem. Contagens com limite inferior positivo são '
        'descritivas; não reclassificam a barreira. Uma variante original falhou '
        '(null_x4, réplica 187, realized_fh, PermissionError em heartbeat); ela '
        'não foi reestimada ou substituída.\n\n'
        '## Diferença por P/N e contribuições\n\n'
        + pn[pn.pn.eq('3G3240V01731')].to_markdown(index=False, floatfmt='.8f') + '\n\n'
        'pn_deltas.csv contém todos os P/N por réplica. pn_aircraft_origin.csv '
        'decompõe cada P/N por aeronave/cópia × origem, com contribuição normalizada '
        'pela agregação original. aggregate_aircraft_origin.csv faz a decomposição '
        'do agregado sem confundir pesos de P/N com pesos de aeronave. As tabelas '
        'guardam média, desvio e quantidade de réplicas presentes.\n\n'
        + focus_contribution.to_markdown(index=False, floatfmt='.8f') + '\n\n'
        '## AC-22, dezembro: probabilidades originais\n\n'
        + focus.to_markdown(index=False, floatfmt='.7f') + '\n\n'
        'Médias entre réplicas para o P/N 3G3240V01731 e as cópias de AC-22, '
        'na origem 2025-12-01. Não são probabilidades da regra corrigida.\n\n'
        '## B=999 versus B=10 000\n\n'
        + aggregate_boot.to_markdown(index=False) + '\n\n'
        'Réplicas fixadas 0–19 de null_x4, ambas as variantes. O recálculo B=999 '
        'reproduz exatamente os intervalos originais, inclusive por P/N. '
        'bootstrap_comparison.csv guarda todos os limites e classificações, '
        'não somente o agregado.\n\n'
        '## Inventário de cobertura nos dados reais\n\n'
        + observed.to_markdown(index=False, floatfmt='.7f') + '\n\n'
        + focus_inventory.to_markdown(index=False, floatfmt='.7f') + '\n\n'
        f'Foram inventariadas {len(tables["window_inventory"])} combinações aeronave × origem, '
        f'{len(affected)} com início da janela anterior ao primeiro registro, '
        f'das quais {int(affected.observed_days.gt(0).sum())} têm cobertura positiva parcial '
        f'e {len(observed)} também têm unidades FH em risco, '
        f'e {len(tables["horizons_after_last_record"])} combinações aeronave × origem × horizonte '
        'com término após o último registro. Os CSV completos incluem casos sem '
        'unidades em risco e saída da aeronave; nenhum horizonte foi corrigido. '
        'Casos sem qualquer registro passado (observed_days=0), inclusive AC-18 '
        'e AC-23 antes de sua entrada, são separados das janelas parciais positivas. '
        'Unidade calendário em risco não implica necessidade de exposição FH.\n\n'
        '## Diagnóstico de implementação e alcance\n\n'
        'Exposure.rates divide o incremento por 90 mesmo na entrada tardia. '
        'A comparação entre exposição prevista e realizada, a contribuição '
        'localizada e a exclusão diagnóstica documentam o defeito descrito pelo '
        'autor. A16 original não estima poder válido para a regra corrigida. '
        'A5/A4 originais continuam como executadas; correções serão errata separada '
        'após o commit da emenda 006. Nenhum resultado desta análise altera '
        'parâmetros do gerador, A16 ou A9.\n')
    (ROOT / 'analysis/a16_null_diagnosis.md').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    main(args.workers)
