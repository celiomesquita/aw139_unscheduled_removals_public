"""A3: document-linked ATA 62 inspection intervals, exploratory sensitivity.

No free text is exported. Same-document inspection is association, not proof
of detection. Previous signed inspection is a provisional last-negative bound.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from feasibility import DERIVED, ROOT, START, END, MIN_EVENTS, load_omth

# Narrow component/task mapping; generic airframe inspections do not establish
# which component was inspected. Damper bolts and rod ends are not mapped.
TASKS = {
    '3G6230A00832': ['139 FIXED S/P AND SCISSORS DI'],
    '3G6230A00833': ['139 FIXED S/P AND SCISSORS DI'],
    '3G6230A00834': ['139 FIXED S/P AND SCISSORS DI'],
    '3G6230A00932': ['139 FIXED S/P AND SCISSORS DI'],
    '3G6230A00934': ['139 FIXED S/P AND SCISSORS DI'],
    '3G6220V01353': ['139 MR DAMPER INSP', '139 MR DAMPER BODY INSP'],
    '3G6220V02051': ['139 MR DAMPER INSP', '139 MR DAMPER BODY INSP'],
}
KEY = ['Part #', 'Serial #', 'Aircraft #', 'att', 'rem']


def construct_intervals(sp, removals, tasks, signoff_tolerance_days=0):
    """Attach bounds requiring aircraft, document, mapped task and close signoff."""
    links = removals[KEY + ['Source Doc #']].drop_duplicates()
    # Ambiguous documents for a spell cannot establish a unique inspection link.
    counts = links.groupby(KEY, dropna=False)['Source Doc #'].nunique()
    links = links.merge(counts.rename('document_count'), on=KEY)
    links = links[links.document_count == 1].drop(columns='document_count').drop_duplicates(KEY)
    out = sp.merge(links, on=KEY, how='left', validate='many_to_one').copy()
    out['lower_date'] = pd.NaT
    out['inspection_task'] = ''
    out['status'] = 'not_target_event'
    out['interval_event'] = False
    for i, r in out.iterrows():
        if not r.event or r['ATA #'] // 100 != 62:
            continue
        mapping = TASKS.get(r['Part #'], [])
        out.at[i, 'status'] = 'unmapped_component'
        if not mapping:
            continue
        relevant = tasks[(tasks['Aircraft #'] == r['Aircraft #']) & tasks['Task #'].isin(mapping)]
        current = relevant[(relevant['Execution Doc #'] == r['Source Doc #']) &
                           ((relevant.d-r.rem).abs().dt.days <= signoff_tolerance_days)]
        out.at[i, 'status'] = 'no_document_inspection_within_tolerance'
        if current.empty:
            continue
        # Previous occurrence of the SAME inspection, during this installation.
        candidates = []
        for task in sorted(current['Task #'].unique()):
            prev = relevant[(relevant['Task #'] == task) & (relevant.d >= r.att) &
                            (relevant.d < r.rem) & (relevant['Execution Doc #'] != r['Source Doc #'])]
            if not prev.empty:
                candidates.append((prev.d.max(), task))
        out.at[i, 'status'] = 'no_previous_inspection_in_spell'
        if not candidates:
            continue
        date, task = max(candidates)
        out.at[i, 'lower_date'] = date
        out.at[i, 'inspection_task'] = task
        out.at[i, 'status'] = 'provisional_interval'
        out.at[i, 'interval_event'] = True
    return out


def mixed_nll(p, lower, upper, event, interval):
    """Weibull likelihood for exact, interval and right-censored observations."""
    beta, eta = np.exp(p)
    with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
        hu, hl = (upper/eta)**beta, (lower/eta)**beta
        exact = event & ~interval
        terms = -hu.copy()
        terms[exact] += np.log(beta) - beta*np.log(eta) + (beta-1)*np.log(upper[exact])
        terms[interval] = -hl[interval] + np.log(-np.expm1(-(hu[interval]-hl[interval])))
        value = -terms.sum()
    return float(value) if np.isfinite(value) else np.inf


def fit_mixed(lower, upper, event, interval):
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    event, interval = np.asarray(event, bool), np.asarray(interval, bool)
    if ((lower < 0) | (upper <= 0) | (lower > upper)).any() or (interval & ~event).any():
        raise ValueError('Invalid survival observations')
    if (upper[interval] <= lower[interval]).any():
        return dict(beta=np.nan, eta=np.nan, beta_lo=np.nan, beta_hi=np.nan, converged=False)
    scale = np.median(upper)
    args = (lower/scale, upper/scale, event, interval)
    results = [minimize(mixed_nll, [np.log(b), 0.], args=args,
                        method='Nelder-Mead', options={'maxiter': 5000}) for b in (.7, 1.5, 3.)]
    res = min(results, key=lambda r: r.fun)
    b, eta = np.exp(res.x)
    h, H = 1e-4, np.zeros((2, 2))
    for i in range(2):
        for j in range(2):
            ei, ej = np.eye(2)[i]*h, np.eye(2)[j]*h
            H[i,j] = (mixed_nll(res.x+ei+ej, *args)-mixed_nll(res.x+ei-ej, *args)
                      -mixed_nll(res.x-ei+ej, *args)+mixed_nll(res.x-ei-ej, *args))/(4*h*h)
    se = np.sqrt(np.linalg.inv(H)[0,0]) if np.isfinite(H).all() and np.linalg.eigvalsh(H).min() > 0 else np.nan
    return dict(beta=b, eta=eta*scale, beta_lo=b*np.exp(-1.96*se), beta_hi=b*np.exp(1.96*se),
                converged=bool(res.success and np.isfinite(res.fun)))


def main():
    sp = pd.read_csv(DERIVED/'spells.csv', parse_dates=['att', 'rem'])
    r = pd.read_csv(DERIVED/'removals_clean.csv', parse_dates=['att', 'rem'])
    tasks = load_omth()
    sp = sp[sp.source.isin(['in_window_removed', 'in_window_censored'])]
    sp = sp[(sp['ATA #']//100 == 62) & (sp.att >= START) & (sp.rem <= END)]
    strict = construct_intervals(sp, r, tasks)
    out = construct_intervals(sp, r, tasks, signoff_tolerance_days=3)
    fh = pd.read_csv(DERIVED/'aircraft_fh_daily.csv', index_col=0, parse_dates=True)
    out['lower_fh'] = np.nan
    for i, row in out[out.interval_event].iterrows():
        out.at[i, 'lower_fh'] = fh.at[row.lower_date, row['Aircraft #']] - fh.at[row.att, row['Aircraft #']]
    out[KEY+['event','Source Doc #','status','lower_date','lower_fh','inspection_task','interval_event']].to_csv(
        DERIVED/'inspection_intervals.csv', index=False)
    rows = []
    for pn, g in out.groupby('Part #'):
        if g.event.sum() < MIN_EVENTS or not g.interval_event.any():
            continue
        # Use identical raw exposure cohort for both fits; never clip zero ages.
        upper = np.array([fh.at[row.rem, row['Aircraft #']]-fh.at[row.att, row['Aircraft #']]
                          for _, row in g.iterrows()])
        positive = upper > 0
        g, upper = g.loc[positive], upper[positive]
        if g.event.sum() < MIN_EVENTS:
            continue
        for mode in ('exact', 'inspection_interval'):
            interval = g.interval_event.to_numpy() if mode != 'exact' else np.zeros(len(g), bool)
            lower = np.where(interval, g.lower_fh.fillna(0), upper)
            fit = fit_mixed(lower, upper, g.event, interval)
            rows.append(dict(pn=pn, mode=mode, spells=len(g), events=int(g.event.sum()),
                             intervals=int(interval.sum()), zero_age_excluded=int((~positive).sum()), **fit))
    fits = pd.DataFrame(rows, columns=['pn','mode','spells','events','intervals','zero_age_excluded',
                                       'beta','eta','beta_lo','beta_hi','converged'])
    fits.to_csv(DERIVED/'inspection_weibull_fits.csv', index=False)
    counts = out[out.event == 1].status.value_counts().rename_axis('status').reset_index(name='events')
    report = f'''# A3 — censura intervalar: associação documental e sensibilidade

Execução: `py -3 analysis/inspection_censoring.py`, após `analysis/feasibility.py`.
Coorte principal, instalações dentro da janela; sem extrapolação pré-2024.

## Protocolo e alcance

Mapa explícito P/N–tarefa em `inspection_censoring.py`: tesouras de rotor
principal e amortecedores. Parafusos, terminais e inspeções genéricas de célula
não recebem associação presumida. Exige mesma aeronave e documento; regra
estrita: assinatura no dia da remoção. Sensibilidade exploratória: assinatura
até três dias antes/depois, sem alterar a data da remoção. A tolerância foi
introduzida após observar defasagem administrativa; não é confirmatória.
Regra estrita: {int(strict.interval_event.sum())} intervalos propostos;
tolerância de três dias: {int(out.interval_event.sum())} intervalos propostos.
Limite inferior: ocorrência anterior da MESMA tarefa, em outro documento, durante a
instalação. Limite superior: remoção. Usa FH não arredondadas artificialmente
por clipping, mas provenientes do relógio diário exportado pela viabilidade.
Eventos não associados permanecem exatos na sensibilidade. Compara ajustes na
mesma coorte com e sem intervalos; idades FH nulas são excluídas de ambos e
contabilizadas. IC 95% Wald em log beta, sem correção de dependência por aeronave.

## Cobertura dos eventos ATA 62

{counts.to_markdown(index=False)}

## Ajustes exploratórios (FH)

{fits.round(4).to_markdown(index=False) if len(fits) else 'Nenhum P/N com cobertura suficiente.'}

## Limites e decisão

Associação no mesmo documento NÃO comprova que a falha foi detectada pela
tarefa, nem que a inspeção anterior foi negativa para o modo de falha relevante.
O mapa de aplicabilidade e os resultados anteriores ainda precisam de validação
documental. Estes intervalos são hipóteses de sensibilidade, não observações
intervalares confirmadas. Não aprovar K1 nem retirar candidatos automaticamente.
Sem essa validação A3 permanece parcial, e os IC não constituem inferência final.
Validação documental complementar: [auditoria dos intervalos](inspection_evidence_report.md),
gerada por `analysis/inspection_evidence.py`. Consultar essa auditoria antes
de interpretar os intervalos como falhas confirmadas.
Não comparar AIC entre os ajustes exato e intervalar: a observação modelada muda.
Artefatos detalhados: `inspection_intervals.csv` e `inspection_weibull_fits.csv`
em `data/derived/`. Nenhum texto livre do operador é exportado.
'''
    (ROOT/'analysis'/'inspection_censoring_report.md').write_text(report, encoding='utf-8')
    print(counts.to_string(index=False))
    print(fits.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
