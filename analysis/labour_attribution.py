"""A6.1: task/removal candidate links and conservative accounting ledger.

Identifiers and component vocabulary provide attribution hypotheses, not causal
labour measurements. Unmatched work remains unallocated.
"""
import hashlib
import re

import numpy as np
import pandas as pd

from feasibility import ANONYMISED, DERIVED, ROOT, load_omth
from removal_labels import COMPONENTS, token_present


def identifier_hit(value, text):
    if pd.isna(value) or str(value).strip().upper() in {'N/A','UNKNOWN','NONE','NIL','NSN','N/S','NOT TRACKED'}:
        return False
    return token_present(value,text)


def link_strength(removal, text):
    """Same-task text may reference removed/installed unit; retain that distinction."""
    if identifier_hit(removal['Serial #'],text):
        return 4,'removed_serial_reference'
    if identifier_hit(removal.get('Attached Serial #'),text):
        return 3,'installed_serial_reference'
    if identifier_hit(removal['Part #'],text):
        return 2,'part_number_reference'
    pattern=COMPONENTS.get(removal['Part #'])
    if pattern and re.search(pattern,text,re.I):
        return 1,'component_family_reference'
    return 0,'unmatched'


def attribute(events,tasks):
    groups={k:g for k,g in events.dropna(subset=['Aircraft #','Source Doc #']).groupby(
        ['Aircraft #','Source Doc #'])}
    links,ledger=[],[]
    for (ac,doc,task),g in tasks.groupby(['Aircraft #','Execution Doc #','Task #']):
        candidates=groups.get((ac,doc))
        if candidates is None:
            continue
        # Aggregate same task once, retaining alternative observed-row vs maximum
        # budgets. Do not export task descriptions or signoff remarks.
        descriptions=sorted(set(g['Task Description'].fillna('').astype(str)))
        remarks=sorted(set(g['Sign Off Remarks'].fillna('').astype(str)))
        text='\n'.join(descriptions+remarks)
        matches=[]
        for _,r in candidates.iterrows():
            strength,reason=link_strength(r,text)
            if strength:
                matches.append((r.cost_event_id,strength,reason))
        # All referenced candidates share the budget; weaker links are retained
        # if another unit is identified, avoiding silently dropping bundled work.
        mh_sum=g['Tot Man Hours'].sum(min_count=1)
        mh_max=g['Tot Man Hours'].max()
        record=dict(aircraft=ac,document=doc,task=task,task_rows=len(g),
            mh_observed_rows=int(g['Tot Man Hours'].notna().sum()),
            mh_row_sum=mh_sum,mh_max=mh_max,candidate_removals=len(matches),
            allocated_mh_row_sum=mh_sum if matches else 0.,
            unallocated_mh_row_sum=0. if matches else mh_sum,
            allocated_mh_max=mh_max if matches else 0.,
            unallocated_mh_max=0. if matches else mh_max)
        ledger.append(record)
        digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
        for event_id,strength,reason in matches:
            links.append(dict(cost_event_id=event_id,aircraft=ac,document=doc,task=task,
                link_strength=strength,link_basis=reason,text_sha256=digest,
                candidate_removals=len(matches),task_rows=len(g),
                mh_observed_rows=record['mh_observed_rows'],
                allocated_mh_row_sum=mh_sum/len(matches),allocated_mh_max=mh_max/len(matches)))
    ledger=pd.DataFrame(ledger)
    columns=['cost_event_id','aircraft','document','task','link_strength','link_basis','text_sha256',
             'candidate_removals','task_rows','mh_observed_rows','allocated_mh_row_sum','allocated_mh_max']
    links=pd.DataFrame(links,columns=columns)
    allocations=links.groupby('cost_event_id').agg(
        candidate_tasks=('task','size'),strongest_link=('link_strength','max'),
        allocated_mh_row_sum=('allocated_mh_row_sum',lambda x:x.sum(min_count=1)),
        allocated_mh_max=('allocated_mh_max',lambda x:x.sum(min_count=1)),
        observed_mh_tasks=('mh_observed_rows',lambda x:int(x.gt(0).sum())))
    result=events[['cost_event_id','Part #','Serial #','Aircraft #','Source Doc #','event']].merge(
        allocations,on='cost_event_id',how='left',validate='one_to_one')
    result['attribution_status']=np.where(result.candidate_tasks.isna(),'no_candidate_task',
        np.where(result.observed_mh_tasks.eq(0),'candidate_tasks_missing_mh','provisional_task_allocation'))
    return links,ledger,result


def main():
    events=pd.read_csv(DERIVED/'event_cost_inputs.csv')
    # Add replacement-unit identifiers by the complete source row identity;
    # event IDs follow the unchanged clean-removal row order in event_costs.py.
    source=pd.read_csv(DERIVED/'removals_clean.csv')
    keys=['Part #','Serial #','Aircraft #','Source Doc #']
    if len(events)!=len(source) or not events[keys].fillna('').equals(source[keys].fillna('')):
        raise ValueError('Cost event order does not match clean removals')
    events['Attached Serial #']=source['Attached Serial #'].to_numpy()
    links,ledger,allocations=attribute(events,load_omth())
    links.to_csv(DERIVED/'task_removal_labour_links.csv',index=False)
    ledger.to_csv(DERIVED/'task_labour_ledger.csv',index=False)
    allocations.to_csv(DERIVED/'event_labour_attribution.csv',index=False)
    for mode in ('row_sum','max'):
        available=ledger['mh_'+mode].sum()
        accounted=ledger['allocated_mh_'+mode].sum()+ledger['unallocated_mh_'+mode].sum()
        if not np.isclose(available,accounted):
            raise ValueError('Task accounting does not conserve observed MH')
    states=allocations.attribution_status.value_counts().rename_axis('status').reset_index(name='removals')
    strengths=links.link_basis.value_counts().rename_axis('basis').reset_index(name='task_removal_links')
    totals=pd.DataFrame([dict(aggregation=m,observed_mh=ledger['mh_'+m].sum(),
        candidate_allocated_mh=ledger['allocated_mh_'+m].sum(),
        unallocated_mh=ledger['unallocated_mh_'+m].sum()) for m in ('row_sum','max')])
    report=f'''# A6.1 — atribuição exploratória de homem-hora por tarefa

Execução: `py -3 analysis/labour_attribution.py`, após `analysis/event_costs.py`.

## Protocolo

Agrupa aeronave/documento/tarefa; consulta descrição e observações para referências
ao serial removido, serial instalado, P/N ou família de componente. Vocabulário de
família cobre somente os 11 P/N candidatos; os identificadores são buscados para
todas as remoções. Marcadores de serial desconhecido não são identificadores.
Mantém vínculos de diferentes forças quando a tarefa pode reunir várias unidades.
Divide o orçamento da tarefa igualmente entre as remoções candidatas, sem atribuir
a elas o trabalho das tarefas sem vínculo. Não pressupõe papel removido/instalado
somente pela menção ao serial. Referências em observações podem refletir reparo/RII,
e não um diagnóstico; servem aqui somente à hipótese de atribuição do trabalho.

## Cobertura

{states.to_markdown(index=False)}

{strengths.to_markdown(index=False)}

## Conservação contábil nas tarefas dos documentos ligados

{totals.round(2).to_markdown(index=False)}

Soma de linhas e máximo por tarefa são agregações alternativas, não limites do
trabalho verdadeiro. Toda tarefa aparece uma vez no livro contábil; cada parcela
alocada tem denominador explícito. MH de tarefa sem candidato permanece não
alocado. Trabalho inteiramente ausente fica ausente, não zero. Os totais somam
somente MH observados; não completam campos parcialmente ausentes.

## Decisão e limites

Os vínculos são hipóteses rastreáveis, sem validação causal ou custo marginal.
Vocabulário incompleto, posição, unidade, inspeção conjunta, citação do componente
instalado e repetição de totais entre assinaturas podem afetar as parcelas.
Incluir tarefa programada por referência ao componente pode incluir trabalho
independente da remoção. Falta validar vínculo, significado do campo de MH e
regra de partilha; não substituir automaticamente o rateio de A6 na otimização.
A ausência de vínculo não equivale a trabalho nulo. Nenhum coeficiente monetário
foi adotado e a função objetivo A7 permanece dependente de A5 e A6.

Artefatos sem texto livre: `task_removal_labour_links.csv`, `task_labour_ledger.csv`
e `event_labour_attribution.csv` em `data/derived/`.
'''
    (ROOT/'analysis'/'labour_attribution_report.md').write_text(report,encoding='utf-8')
    print(states.to_string(index=False))
    print(totals.round(2).to_string(index=False))


if __name__=='__main__':
    main()
