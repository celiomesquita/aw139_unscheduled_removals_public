"""T9: descriptive reanalysis of frozen A4 predictions; no model fitting."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from a5_validation import bootstrap_decision, metrics
from machine_reproduction import OLD_HOST_ATOL, OLD_HOST_RTOL, compare_old_frame

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'data/derived/a4'
OUT = ROOT / 'data/derived/a15'


def protected_hashes():
    paths = [p for folder in ('a4', 'a5')
             for p in (ROOT / 'data/derived' / folder).rglob('*') if p.is_file()]
    paths += [ROOT / 'analysis' / f'preregistro_{name}.md' for name in ('A4', 'A5')]
    paths += [ROOT / 'paper/manuscript.tex']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def main():
    before = protected_hashes()
    OUT.mkdir(exist_ok=True)
    aircraft = sorted(pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv')['Aircraft #'].dropna().unique())
    keep = pd.read_csv(ROOT / 'data/derived/k1_candidates.csv')
    candidates = sorted(keep.loc[keep.retained, 'pn'])
    original = pd.read_csv(SOURCE / 'intervals.csv', float_precision='round_trip')
    original_metrics = pd.read_csv(SOURCE / 'metrics.csv', float_precision='round_trip')
    intervals, scores, calibrations, comparisons = [], [], [], []
    old_host_checks = []
    for variant in ('principal', 'realized_fh'):
        frame = pd.read_csv(SOURCE / f'predictions_{variant}.csv', parse_dates=['origin'],
                            float_precision='round_trip')
        periods = {'2025': frame, 'jan-jun': frame[frame.origin.dt.month.le(6)],
                   'jul-dez': frame[frame.origin.dt.month.ge(7)]}
        for period, subset in periods.items():
            # All eleven P/N must be represented: retain original Bonferroni family.
            if set(subset.pn) != set(candidates):
                raise ValueError('Incomplete PN coverage; do not silently change multiplicity')
            m, c = metrics(subset)
            if period == '2025':
                saved_metrics = original_metrics[original_metrics.variant.eq(variant)].set_index(['model', 'pn'])
                columns = ['log_score', 'brier', 'unit_predictions', 'fallback_share']
                # T17b: only the comparison with frozen Windows A4 outputs.
                column_report = {}
                old_host_checks.append(dict(kind='metrics', variant=variant, artifact='data/derived/a4/metrics.csv', columns=column_report,
                    max_abs_difference=compare_old_frame(
                        m.set_index(['model', 'pn'])[columns].loc[saved_metrics.index],
                        saved_metrics[columns], column_report)))
            for obj in (m, c):
                obj['variant'], obj['period'] = variant, period
            scores.append(m[m.model.isin(['w_selected', 'e_selected', 'baseline'])])
            calibrations.append(c[c.model.isin(['w_selected', 'e_selected', 'baseline'])])
            for criterion in ('K2-A4', 'K2-idade'):
                paired = subset.copy()
                if criterion == 'K2-idade':
                    paired['baseline'] = paired.e_selected
                decision, ci, _ = bootstrap_decision(paired, aircraft, candidates)
                if period == '2025':
                    saved = original[(original.variant == variant) &
                                     (original.aggregation == 'aircraft') &
                                     (original.criterion == criterion)].set_index('pn')
                    columns = ['delta_log', 'ci_lo', 'ci_hi', 'simultaneous_lo',
                               'simultaneous_hi', 'missing_replicates']
                    column_report = {}
                    old_host_checks.append(dict(kind='intervals', variant=variant, criterion=criterion, artifact='data/derived/a4/intervals.csv', columns=column_report,
                        max_abs_difference=compare_old_frame(
                            ci.set_index('pn')[columns].loc[saved.index], saved[columns], column_report)))
                    saved_passed = sorted(saved.index[(saved.index != 'aggregate') & saved.simultaneous_lo.gt(0)])
                    current_passed = sorted(ci.loc[ci.pn.ne('aggregate') & ci.simultaneous_lo.gt(0), 'pn'])
                    saved_outcome = ('favoravel' if saved.loc['aggregate', 'ci_lo'] > 0
                                     else 'mista' if saved_passed else 'nula')
                    if decision != saved_outcome or current_passed != saved_passed:
                        raise AssertionError('T17b: historical K2/Bonferroni decision changed')
                    small, ci999, _ = bootstrap_decision(paired, aircraft, candidates, reps=999)
                    passed = lambda x: sorted(x.loc[x.pn.ne('aggregate') & x.simultaneous_lo.gt(0), 'pn'])
                    comparisons.append(dict(variant=variant, criterion=criterion,
                        B10000=decision, B999=small, same_decision=decision == small,
                        passed10000=';'.join(passed(ci)), passed999=';'.join(passed(ci999)),
                        same_PN=passed(ci) == passed(ci999)))
                # No decision labels are exported for descriptive half-year results.
                ci['variant'], ci['period'], ci['criterion'] = variant, period, criterion
                ci['predictions'], ci['aircraft'] = len(subset), subset.aircraft.nunique()
                intervals.append(ci)
    pd.concat(intervals).to_csv(OUT / 'intervals.csv', index=False)
    pd.concat(scores).to_csv(OUT / 'metrics.csv', index=False)
    pd.concat(calibrations).to_csv(OUT / 'calibration.csv', index=False)
    check = pd.DataFrame(comparisons)
    check.to_csv(OUT / 'bootstrap_check.csv', index=False)
    result = pd.concat(intervals)
    table = result[result.pn.eq('aggregate')][['variant', 'period', 'criterion',
        'delta_log', 'ci_lo', 'ci_hi', 'predictions', 'aircraft']]
    report = ('# A15 — robustez descritiva temporal\n\n'
        'Desenho posterior ao conhecimento de A4. Previsões congeladas, sem novo ajuste. '
        'Origens jan–jun e jul–dez/2025; os alvos de horizontes sobrepostos não são '
        'amostras independentes. Nenhuma regra de decisão é aplicada aos semestres.\n\n'
        'Mesmo código de métricas e bootstrap de A5/A4: 24 códigos de aeronave, '
        '10 000 reamostragens, PCG64 20261112, agregação por aeronave e Bonferroni '
        'para 11 P/N. IC 95% descritivos; não corrigidos entre semestres/variantes.\n\n'
        + table.to_markdown(index=False, floatfmt='.6f') + '\n\n'
        'As 12 origens reproduzem os intervalos publicados de A4 pela regra T17b '
        '(T17c: atol=1e-8, rtol=1e-6 entre máquinas; sinais e decisões exatos), além de log score, Brier, '
        'contagens e fallback de todos os modelos publicados. Detalhes por P/N em '
        '`data/derived/a15/intervals.csv`; métricas e calibração nos CSV adjacentes.\n\n'
        'Na variante principal, o ganho médio da idade é positivo em jan–jun e '
        'negativo em jul–dez. Com FH realizadas, os dois valores pontuais são '
        'positivos, com maior incerteza no segundo semestre. Isso descreve '
        'variação temporal; não é um teste independente de mudança nem altera '
        'K2-idade. O agregado anual não é a média simples dos semestres: a '
        'composição de aeronaves e origens observáveis difere.\n\n'
        '## Verificação B = 999 para o futuro A16\n\n' + check.to_markdown(index=False)
        + '\n\nEsta comparação verifica decisões reais; não estabelece equivalência '
        'de caudas Monte Carlo em todas as futuras amostras sintéticas. FH realizadas '
        'permanece hipótese gerada pelos dados, sem confirmação independente.\n')
    (ROOT / 'analysis/a15_report.md').write_text(report, encoding='utf-8')
    if before != protected_hashes():
        raise RuntimeError('Protected A4/A5/manuscript files changed')
    (OUT / 'manifest.json').write_text(json.dumps(dict(protected=before,
        full_year_reproduced=True, absolute_tolerance=OLD_HOST_ATOL, relative_tolerance=OLD_HOST_RTOL, fits_executed=0,
        old_host_checks=old_host_checks, same_host_comparison='bitwise'),
        indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(table.to_string(index=False))
    print(check.to_string(index=False))


if __name__ == '__main__':
    main()
