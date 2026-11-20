"""A6: observed cost inputs and explicitly bounded operational proxies.

No hourly labour rate, downtime price or outside-visit penalty is inferred.
"""
import numpy as np
import pandas as pd

from feasibility import ANONYMISED, DERIVED, ROOT, END, STOP_GAP_DAYS, load_omth


def document_labour(tasks):
    """Original-row and per-task-maximum aggregations expose repeated MH ambiguity."""
    keys = ['Aircraft #','Execution Doc #']
    raw = tasks.groupby(keys).agg(task_rows=('Task #','size'),
        mh_observed_rows=('Tot Man Hours','count'),
        mh_row_sum=('Tot Man Hours', lambda x:x.sum(min_count=1)))
    taskmax = tasks.groupby(keys+['Task #'])['Tot Man Hours'].max()
    proxy = taskmax.groupby(level=[0,1]).sum(min_count=1).rename('mh_task_max_sum')
    return raw.join(proxy).reset_index()


def flight_gaps(removals, flights, end=END):
    """One episode per aircraft/date; dates bound the next-flight gap, not downtime."""
    positive = flights[flights.Hours.gt(0)].copy()
    positive['d'] = pd.to_datetime(positive['Flight Date'],format='%d/%m/%Y')
    positive = positive[positive.d.le(end)]
    flight_days = {ac:pd.DatetimeIndex(g.d.unique()).sort_values()
                   for ac,g in positive.groupby('Aircraft #')}
    episodes = removals[removals.event.eq(1)].dropna(subset=['Aircraft #','rem']).groupby(
        ['Aircraft #','rem']).size().rename('removals').reset_index()
    rows=[]
    for row in episodes.itertuples(index=False,name=None):
        ac, date, count = row
        dates = flight_days.get(ac,pd.DatetimeIndex([]))
        same = date in dates
        later = dates[dates>date]
        observed = len(later)>0
        next_day = later[0] if observed else pd.NaT
        days = (next_day-date).days if observed else np.nan
        # If a flight occurred on removal day its position relative to the
        # removal is unknown. It prevents a positive lower bound.
        lower = (0 if same else max(0,days-1)*24) if observed else (
            0 if same else max(0,(end-date).days)*24)
        upper = (days+1)*24 if observed else np.nan
        rows.append(dict(aircraft=ac,removal_date=date,removals=count,
            flight_on_removal_day=same,next_later_flight_date=next_day,
            later_flight_observed=observed,gap_lower_hours=lower,gap_upper_hours=upper,
            window_end_without_later_flight=not observed))
    return pd.DataFrame(rows)


def event_inputs(removals, labour, visits):
    r=removals.copy().reset_index(drop=True)
    r['cost_event_id']=['C'+str(i+1).zfill(5) for i in r.index]
    keys=['Aircraft #','Source Doc #']
    valid=r.dropna(subset=keys)
    counts=valid.groupby(keys).size().rename('removals_in_document').reset_index()
    r=r.merge(counts,on=keys,how='left',validate='many_to_one')
    r=r.merge(labour,left_on=keys,right_on=['Aircraft #','Execution Doc #'],how='left',validate='many_to_one')
    r['document_linked']=r['Execution Doc #'].notna()
    for name in ['mh_row_sum','mh_task_max_sum']:
        r[name+'_equal_share']=r[name]/r.removals_in_document
    r['inside_visit_proxy']=pd.Series(pd.NA,index=r.index,dtype='boolean')
    for ac,g in r.groupby('Aircraft #'):
        v=visits[visits['Aircraft #'].eq(ac)]
        for idx,date in g.rem.items():
            if pd.isna(date):
                continue
            r.at[idx,'inside_visit_proxy']=bool(((v.start-pd.Timedelta(days=STOP_GAP_DAYS)<=date)&
                (date<=v.end+pd.Timedelta(days=STOP_GAP_DAYS))).any())
    # Catalogue values are retained as observations, not replacement expenditure.
    return r


def main():
    r=pd.read_csv(DERIVED/'removals_clean.csv',parse_dates=['att','rem'])
    tasks=load_omth()
    visits=pd.read_csv(DERIVED/'stoppages.csv',parse_dates=['start','end'])
    labour=document_labour(tasks)
    events=event_inputs(r,labour,visits)
    gaps=flight_gaps(r,pd.read_csv(ANONYMISED/'hours_flown.csv'))
    keep=['cost_event_id','Part #','Serial #','Aircraft #','Source Doc #','rem','event',
          'Std Cost','document_linked','removals_in_document','task_rows','mh_observed_rows',
          'mh_row_sum','mh_task_max_sum','mh_row_sum_equal_share','mh_task_max_sum_equal_share',
          'inside_visit_proxy']
    events[keep].to_csv(DERIVED/'event_cost_inputs.csv',index=False)
    labour.to_csv(DERIVED/'document_labour_proxies.csv',index=False)
    gaps.to_csv(DERIVED/'return_to_flight_gaps.csv',index=False)
    u=events[events.event.eq(1)]
    used=events[events.document_linked].drop_duplicates(['Aircraft #','Source Doc #'])
    summary=pd.DataFrame([
        ('Removals',len(events)),('Unscheduled removals',len(u)),
        ('Linked removals',int(events.document_linked.sum())),
        ('Linked unscheduled removals',int(u.document_linked.sum())),
        ('Linked documents',len(used)),
        ('Linked documents with some missing MH',int(used.mh_observed_rows.lt(used.task_rows).sum())),
        ('Unscheduled aircraft-day episodes',len(gaps)),
        ('Episodes with flight on removal day',int(gaps.flight_on_removal_day.sum())),
        ('Episodes without later flight in window',int(gaps.window_end_without_later_flight.sum())),
    ],columns=['quantity','value'])
    costs=u.groupby('inside_visit_proxy',dropna=False).agg(removals=('cost_event_id','size'),
        median_catalogue_cost=('Std Cost','median'),
        median_mh_row_share=('mh_row_sum_equal_share','median'),
        median_mh_task_max_share=('mh_task_max_sum_equal_share','median')).reset_index()
    costs['inside_visit_proxy']=costs.inside_visit_proxy.map({True:'inside',False:'outside'}).fillna('unknown')
    report=f'''# A6 — evidências para custo e retorno ao voo

Execução: `py -3 analysis/event_costs.py`, após `analysis/feasibility.py`.

## Cobertura observada

{summary.to_markdown(index=False)}

{costs.round(2).to_markdown(index=False)}

## Homem-hora

Ligação por aeronave E documento, sem depender de diagnóstico lexical. Soma das
linhas originais do OMTH e, como sensibilidade a múltiplas assinaturas, soma dos
máximos por tarefa/documento. As duas agregações são proxies, não limites formais
do trabalho verdadeiro. Linhas repetidas podem representar duplicação ou trabalho
legítimo; não são apagadas silenciosamente. Documento inteiramente sem MH fica
ausente, não zero; documento parcialmente preenchido conserva marcador de cobertura.
Rateio igual por todas as remoções do documento, incluindo programadas, apenas
como referência contábil. Inclui tarefas possivelmente não relacionadas à remoção;
não identifica homem-hora causal nem custo marginal por evento. Somar rateios não
cria trabalho adicional, mas não corrige a atribuição a tarefas independentes.

## Retorno ao voo e oportunidade de visita

Uma linha por aeronave/dia de remoção não programada evita contar o mesmo intervalo
várias vezes. Voo observado exige Hours > 0; registros com horas ausentes não são
automaticamente evidência de voo. Primeiro voo em dia estritamente posterior à
remoção: {gaps.loc[gaps.later_flight_observed,'gap_upper_hours'].median():.1f} h de
limite superior mediano, sob datas sem horário. Com diferença de k dias, a faixa
é [max(0,k−1),k+1] × 24 h; voo no dia da remoção impõe limite inferior zero, pois
a ordem é desconhecida. Sem voo posterior, o fim da janela limita a observação;
voo no mesmo dia impede afirmar censura à direita da verdadeira duração.
Limites pressupõem extrato de voos completo; não imputam voos não registrados.

Esses intervalos são proxies do retorno ao voo, não indisponibilidade causal:
demanda operacional, outras tarefas e esperas podem determinar a próxima saída.
Visitas usam as janelas da viabilidade com tolerância de ±{STOP_GAP_DAYS} dias;
coincidência não comprova aproveitamento da mesma parada. Registros sem aeronave
ou data mantêm oportunidade de visita desconhecida (NA). Não somar intervalos
por componente nem interpretar diferença dentro/fora de visita como efeito causal.

## Decisão e pendências

Preço de catálogo preservado separadamente de custo realizado. Não soma USD,
homem-hora e horas de intervalo sem coeficientes de conversão fundamentados.
Taxa horária de mão de obra, valor de indisponibilidade e penalidade fora de visita
permanecem sem valor adotado. Defini-los e registrar faixas de sensibilidade antes
de A8/A9; evitar cobrar duas vezes indisponibilidade na penalidade e no termo de
tempo. A6 permanece parcial; estes dados ainda não definem a função objetivo A7.
Mesmo sem confirmação física de A3, A6 fornece insumos operacionais auditáveis.

Artefatos: `data/derived/event_cost_inputs.csv`, `document_labour_proxies.csv`
e `return_to_flight_gaps.csv`. Não exporta texto livre do operador.
'''
    (ROOT/'analysis'/'event_costs_report.md').write_text(report,encoding='utf-8')
    print(summary.to_string(index=False))
    print(costs.round(2).to_string(index=False))


if __name__=='__main__':
    main()
