"""T4: single-removal document inputs and noncausal flight-gap contrasts."""
import numpy as np
import pandas as pd

from feasibility import DERIVED, ROOT


def single_removal_documents(events):
    counts=events.dropna(subset=['Aircraft #','Source Doc #']).groupby(
        ['Aircraft #','Source Doc #']).size().rename('all_removal_count')
    joined=events.merge(counts,on=['Aircraft #','Source Doc #'],how='left',validate='many_to_one')
    return joined[joined.all_removal_count.eq(1) & joined.event.eq(1) & joined.document_linked].copy()


def quantiles(values):
    values=values.dropna()
    return dict(n_observed=len(values),median=values.median(),q1=values.quantile(.25),q3=values.quantile(.75))


def summarize(single,events):
    rows=[]
    for pn,g in events[events.event.eq(1)].groupby('Part #'):
        one=single[single['Part #'].eq(pn)]
        for mode,column in [('row_sum','mh_row_sum'),('task_max','mh_task_max_sum')]:
            for cohort,values in [('single_document',one[column]),
                                  ('all_equal_share',g[column+'_equal_share'])]:
                rows.append(dict(pn=pn,aggregation=mode,cohort=cohort,
                                 documents=len(one) if cohort=='single_document' else
                                 len(g[['Aircraft #','Source Doc #']].dropna().drop_duplicates()),
                                 **quantiles(values)))
    return pd.DataFrame(rows)


def gap_summary(gaps,events):
    u=events[events.event.eq(1)].dropna(subset=['Aircraft #','rem'])
    visits=u.groupby(['Aircraft #','rem']).inside_visit_proxy.first().reset_index()
    x=gaps.merge(visits,left_on=['aircraft','removal_date'],right_on=['Aircraft #','rem'],
                 how='left',validate='one_to_one')
    rows=[]
    for flag,label in [(True,'inside'),(False,'outside')]:
        g=x[x.inside_visit_proxy.eq(flag)]
        # Contrasts require common episodes with a finite upper bound. Episodes
        # without a later flight remain in the coverage counts, not imputed.
        complete=g[g.later_flight_observed]
        for bound in ('lower','upper'):
            rows.append(dict(visit=label,bound=bound,total_episodes=len(g),
                without_later_flight=int((~g.later_flight_observed).sum()),
                **quantiles(complete['gap_'+bound+'_hours'])))
    return pd.DataFrame(rows)


def validate_parameters(parameters):
    if list(parameters.columns)!=['parametro','valor_central','faixa_min','faixa_max','fonte']:
        raise ValueError('Invalid cost parameter schema')
    if parameters.parametro.duplicated().any() or parameters.fonte.isna().any():
        raise ValueError('Cost parameters must be unique and sourced')
    for row in parameters.itertuples():
        values=[row.valor_central,row.faixa_min,row.faixa_max]
        if all(str(v)=='AUTOR_DEFINIR' for v in values):
            continue
        numeric=np.array(values,dtype=float)
        if not np.isfinite(numeric).all() or not numeric[1]<=numeric[0]<=numeric[2]:
            raise ValueError('Invalid numeric parameter range')


def main():
    events=pd.read_csv(DERIVED/'event_cost_inputs.csv',parse_dates=['rem'])
    gaps=pd.read_csv(DERIVED/'return_to_flight_gaps.csv',parse_dates=['removal_date'])
    single=single_removal_documents(events)
    stats=summarize(single,events)
    gapstats=gap_summary(gaps,events)
    single.to_csv(DERIVED/'single_removal_cost_documents.csv',index=False)
    stats.to_csv(DERIVED/'single_removal_mh_summary.csv',index=False)
    gapstats.to_csv(DERIVED/'visit_gap_summary.csv',index=False)
    parameters=[]
    def add(name,central,lo,hi,source='dados'):
        parameters.append(dict(parametro=name,valor_central=central,faixa_min=lo,faixa_max=hi,fonte=source))
    for row in stats[stats.cohort.eq('single_document') & stats.n_observed.gt(0)].itertuples():
        add(f'mh_{row.aggregation}_{row.pn}',row.median,row.q1,row.q3)
    for pn,g in events[events.event.eq(1)].groupby('Part #'):
        q=quantiles(g['Std Cost'])
        if q['n_observed']:
            add(f'catalogue_usd_{pn}',q['median'],q['q1'],q['q3'])
    for row in gapstats.itertuples():
        add(f'gap_{row.visit}_{row.bound}_hours',row.median,row.q1,row.q3)
    s=gapstats.set_index(['visit','bound'])
    lo=s.at[('outside','lower'),'median']-s.at[('inside','upper'),'median']
    hi=s.at[('outside','upper'),'median']-s.at[('inside','lower'),'median']
    midpoint=(lo+hi)/2
    add('gap_outside_minus_inside_hours_diagnostic',midpoint,lo,hi)
    for name in ('labour_usd_per_mh','opportunity_usd_per_aircraft_day'):
        add(name,'AUTOR_DEFINIR','AUTOR_DEFINIR','AUTOR_DEFINIR','AUTOR_DEFINIR')
    p=pd.DataFrame(parameters)
    validate_parameters(p)
    p.to_csv(ROOT/'config'/'cost_parameters.csv',index=False)
    report=f'''# T4 — coeficientes empíricos e parâmetros pendentes

Execução: `py -3 analysis/round2_costs.py`, após `event_costs.py`.

## Documento com uma remoção

Filtro conta TODAS as remoções no par aeronave/documento antes de selecionar a
única remoção não programada. Entram {len(single)} documentos, dos quais
{int(single.mh_row_sum.notna().sum())} têm algum MH observado.
MH ausente não vira zero. As medianas, Q1 e Q3 por P/N, para soma de linhas e
soma dos máximos por tarefa, e a comparação com rateio igual estão em
`data/derived/single_removal_mh_summary.csv` ({stats.pn.nunique()} P/N).
Documento único reduz a ambiguidade entre remoções, mas pode conter tarefas
independentes. Não transforma seu total em MH causal da remoção. A6.1 permanece
sensibilidade; estes coeficientes são a fonte principal autorizada em T4.

## Retorno ao voo por episódio

{gapstats.round(3).to_markdown(index=False)}

Fora − dentro: diferença das medianas dos limites inferiores =
{s.at[('outside','lower'),'median']-s.at[('inside','lower'),'median']:.3f} h;
diferença das medianas dos limites superiores =
{s.at[('outside','upper'),'median']-s.at[('inside','upper'),'median']:.3f} h.
Faixa de contraste por extremos: [{lo:.3f}, {hi:.3f}] h; ponto central descritivo
{midpoint:.3f} h. Não é IC estatístico nem efeito causal. Usa os mesmos episódios
com voo posterior para os dois limites; episódios sem voo posterior ficam nas
contagens de cobertura. Diferenças não positivas não são truncadas para fabricar
uma penalidade favorável. Coocorrência com visita segue o proxy de A6.

## Coeficientes e dupla contagem

`config/cost_parameters.csv`: esquema parametro, valor_central, faixa_min,
faixa_max, fonte. Dados empíricos têm fonte dados; faixa de MH/preço/gap por
grupo é IQR, enquanto a faixa do contraste usa extremos de medianas.
Taxa horária e custo de oportunidade por aeronave-dia: AUTOR_DEFINIR.
Não há conversão monetária nem objetivo executado.

Na representação com tempo total do episódio, o termo de oportunidade será
custo_dia × gap_horas/24. A diferença fora−dentro é DIAGNÓSTICA e NÃO é somada
novamente como penalidade temporal. Alternativa de decomposição: tempo de visita
mais incremento fora de visita, substituindo o tempo total, nunca acumulando as
duas representações. Penalidade adicional fixa exigiria evidência de custo
distinto (mobilização etc.), ausente; nenhum valor foi inventado.

T4 concluída com coeficientes empíricos e duas decisões do autor pendentes.
A6 permanece parcial até essas definições; isso não bloqueia A5.
'''
    (ROOT/'analysis'/'round2_costs_report.md').write_text(report,encoding='utf-8')
    print(f'Single-removal documents: {len(single)}; MH observed: {single.mh_row_sum.notna().sum()}')
    print(gapstats.to_string(index=False))
    print(f'Outside-inside diagnostic range: [{lo}, {hi}] hours')


if __name__=='__main__':
    main()
