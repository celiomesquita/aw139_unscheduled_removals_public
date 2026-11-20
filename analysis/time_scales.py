"""A2 exploratory comparison on a common daily observation measure.

Run after feasibility.py: py -3 analysis/time_scales.py.
Take-offs are a cycle proxy, not a validated landing counter.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from feasibility import ANONYMISED, DERIVED, START, END, MIN_EVENTS, ROOT


def cycle_clock(h):
    """Cumulative observed cycles and cumulative missing-record count per aircraft."""
    h = h.copy()
    h['d'] = pd.to_datetime(h['Flight Date'], format='%d/%m/%Y')
    h['missing'] = h['Take Off'].isna().astype(int)
    daily = h.groupby(['d', 'Aircraft #']).agg(
        cycles=('Take Off', 'sum'), missing=('missing', 'sum'))
    days = pd.date_range(START, END)
    return tuple(daily[c].unstack().reindex(days).fillna(0).cumsum()
                 for c in ('cycles', 'missing'))


def daily_nll(p, lower, upper, event):
    """Failures in (lower, upper]; survivors through upper (entry at age zero)."""
    beta, eta = np.exp(p)
    with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
        hu = (upper / eta) ** beta
        hl = (lower / eta) ** beta
        delta = hu - hl
        logp = -hl[event] + np.log(-np.expm1(-delta[event]))
        value = hu[~event].sum() - logp.sum()
    return float(value) if np.isfinite(value) else np.inf


def fit_daily(lower, upper, event):
    lower, upper = np.asarray(lower), np.asarray(upper)
    event = np.asarray(event, dtype=bool)
    if (upper < lower).any() or (lower < 0).any():
        raise ValueError('Invalid exposure interval')
    if not event.any() or (upper[event] <= lower[event]).any():
        return dict(beta=np.nan, eta=np.nan, aic=np.nan, converged=False)
    scale = np.median(upper[upper > 0])
    results = [minimize(daily_nll, [np.log(b), 0.0],
                        args=(lower / scale, upper / scale, event),
                        method='Nelder-Mead', options={'maxiter': 3000})
               for b in (0.7, 1.5, 3.0)]
    res = min(results, key=lambda r: r.fun)
    beta, eta = np.exp(res.x)
    return dict(beta=beta, eta=eta * scale, aic=4 + 2 * res.fun,
                converged=bool(res.success and np.isfinite(res.fun)))


def select_scale(scores):
    """Keep FH unless another converged scale improves AIC by at least two."""
    valid = scores[scores.converged & scores.aic.notna()]
    fh = valid[valid.scale == 'FH']
    if fh.empty:
        return 'unresolved'
    best = valid.loc[valid.aic.idxmin()]
    return best.scale if float(fh.aic.iloc[0]) - best.aic >= 2 else 'FH'


def compare(sp, fh, cycles, missing, require_cycles=True):
    rows, coverage = [], []
    primary = sp[sp.source.isin(['in_window_removed', 'in_window_censored'])].copy()
    for pn, group in primary.groupby('Part #'):
        if group.event.sum() < MIN_EVENTS:
            continue
        exposures = []
        exclusions = dict(invalid_dates=0, missing_clock=0, missing_cycles=0)
        for _, r in group.iterrows():
            ac, att, end = r['Aircraft #'], r.att, r.rem
            # Both dates denote end-of-day readings; no within-day order is available.
            if pd.isna(att) or pd.isna(end) or not START <= att < end <= END:
                exclusions['invalid_dates'] += 1
                continue
            if ac not in fh or (require_cycles and ac not in cycles):
                exclusions['missing_clock'] += 1
                continue
            if require_cycles and missing.at[end, ac] != missing.at[att, ac]:
                exclusions['missing_cycles'] += 1
                continue
            prev = end - pd.Timedelta(days=1)
            exposures.append((bool(r.event),
                fh.at[prev, ac] - fh.at[att, ac], fh.at[end, ac] - fh.at[att, ac],
                (prev - att).days, (end - att).days,
                cycles.at[prev, ac] - cycles.at[att, ac] if require_cycles else np.nan,
                cycles.at[end, ac] - cycles.at[att, ac] if require_cycles else np.nan))
        x = np.asarray(exposures, dtype=float).reshape(-1, 7)
        coverage.append(dict(pn=pn, total=len(group), retained=len(x),
                             events=int(x[:, 0].sum()), excluded=len(group)-len(x), **exclusions))
        if x[:, 0].sum() < MIN_EVENTS:
            continue
        for scale, col in [('FH', 1), ('calendar', 3), ('takeoffs', 5)]:
            if scale == 'takeoffs' and not require_cycles:
                continue
            fit = fit_daily(x[:, col], x[:, col + 1], x[:, 0])
            rows.append(dict(pn=pn, scale=scale, spells=len(x), events=int(x[:, 0].sum()),
                             zero_exposure_events=int(((x[:, col+1] <= x[:, col]) & (x[:, 0] == 1)).sum()), **fit))
    fits = pd.DataFrame(rows)
    choices = pd.DataFrame([dict(pn=pn, selected=select_scale(g))
                            for pn, g in fits.groupby('pn')])
    return fits, pd.DataFrame(coverage), choices


def main():
    sp = pd.read_csv(DERIVED / 'spells.csv', parse_dates=['att', 'rem'])
    fh = pd.read_csv(DERIVED / 'aircraft_fh_daily.csv', index_col=0, parse_dates=True)
    cycles, missing = cycle_clock(pd.read_csv(ANONYMISED / 'hours_flown.csv'))
    fits, coverage, choices = compare(sp, fh, cycles, missing)
    fits.to_csv(DERIVED / 'time_scale_fits.csv', index=False)
    coverage.to_csv(DERIVED / 'time_scale_coverage.csv', index=False)
    choices.to_csv(DERIVED / 'time_scale_choices.csv', index=False)
    broad_fits, broad_coverage, broad_choices = compare(sp, fh, cycles, missing, require_cycles=False)
    broad_fits.to_csv(DERIVED / 'time_scale_broad_fits.csv', index=False)
    broad_coverage.to_csv(DERIVED / 'time_scale_broad_coverage.csv', index=False)
    broad_choices.to_csv(DERIVED / 'time_scale_broad_choices.csv', index=False)
    report = f'''# A2 — comparação exploratória de escalas de tempo

Gerado por `py -3 analysis/time_scales.py`, após `analysis/feasibility.py`.

## Protocolo

Coorte principal de instalações dentro da janela, entrada na idade zero.
Comparação pareada nas mesmas instalações para FH, calendário e decolagens.
AIC = 4 − 2 log L, usando a probabilidade do evento no intervalo diário
(dia anterior, remoção] e sobrevivência até a remoção nas censuras.
Assim, todas as verossimilhanças usam a mesma medida observacional, evitando
comparar densidades expressas em unidades diferentes. Relógios no fim do dia;
instalações e remoções no mesmo dia são excluídas por ordem desconhecida.
Nenhum contador ausente é imputado: trechos com registros de decolagem ausentes
entre instalação (exclusiva) e remoção são excluídos de todas as escalas.
Dias sem registros são tratados como sem voo, sujeito à completude do extrato.
Eventos sem exposição no último dia tornam a escala incompatível com este
protocolo; ficam sem ajuste, sem eliminar o evento ou inventar exposição.
Mínimo de {MIN_EVENTS} falhas após as exclusões. Mantém FH em empate;
alterna somente com melhoria de AIC ≥ 2 e convergência.

## Cobertura e resultados

{coverage.to_markdown(index=False)}

{choices.to_markdown(index=False)}

## FH–calendário sem exigir contadores de ciclos

Mesma regra diária e mesma coorte dentro de cada comparação, mas sem excluir
trechos por decolagens ausentes. Cobertura e ajustes completos nos arquivos
`data/derived/time_scale_broad_*.csv`. A seleção permanece inconclusiva quando
FH atribui probabilidade zero a qualquer evento; não se escolhe calendário
automaticamente por esse motivo.

{broad_coverage.to_markdown(index=False)}

{broad_choices.to_markdown(index=False)}

## Limites e próxima decisão

Resultados exploratórios, sem aprovação de K1 ou K2. A coorte completa pode
ser seletiva; avaliar os trechos excluídos antes de adoptar a escala. Decolagens
são proxy de ciclos, ainda sem validação como pousos. Achados em inspeção
continuam limitados ao último dia: A3 deve ampliar o intervalo para a última
inspeção pertinente. A escolha definitiva depende de A3 e da validação temporal
de A5. Não há inferência sobre economia ou eficácia de política.
'''
    (ROOT / 'analysis' / 'time_scales_report.md').write_text(report, encoding='utf-8')
    print(choices.to_string(index=False))


if __name__ == '__main__':
    main()
