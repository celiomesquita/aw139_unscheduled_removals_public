"""Source review of inconclusive candidate removals; no physical labels inferred.

Reviewed task codes below refer to descriptions read in this analysis round.
Other descriptions are retrieval candidates, not adjudicated observations.
"""
import hashlib
import re

import pandas as pd

from feasibility import DERIVED, ROOT, load_omth
from removal_labels import screen, token_present

# Source Task Description review, not repair signoff interpretation. Categories
# describe text only; canvas visibility is not assumed to exceed an AMM limit.
REVIEWED = {
    'ALNST-017991-2024': 'wear_no_threshold',
    'ALNST-018138-2024': 'canvas_visible_no_threshold',
    'ALNST-018461-2024': 'replacement_or_rii_only',
    'ALNST-018699-2024': 'wear_no_threshold',
    'ALNST-018800-2024': 'damage_no_functional_loss_stated',
    'ALNST-018801-2024': 'damage_no_functional_loss_stated',
    'ALNST-018803-2024': 'broken_ceramic_no_functional_loss_stated',
    'ALNST-018813-2024': 'excessive_wear_stated',
    'ALNST-018829-2024': 'maintenance_convenience',
    'ALNST-018971-2024': 'replacement_or_rii_only',
    'ALNST-018789-2024': 'poor_condition_no_threshold',
    'ALNST-019028-2024': 'wear_no_threshold',
    'ALNST-019157-2024': 'uneven_wear_no_threshold',
    'ALNST-019315-2024': 'canvas_visible_no_threshold',
    'ALNST-019341-2024': 'replacement_or_rii_only',
    'ALNST-019443-2024': 'play_no_threshold',
    'ALNST-019444-2024': 'play_no_threshold',
    'ALNST-019541-2024': 'scratched_no_functional_loss_stated',
    'ALNST-019657-2024': 'canvas_visible_no_threshold',
    'ALNST-019660-2024': 'near_limit',
    'ALNST-019794-2024': 'wear_no_threshold',
    'ALNST-019954-2024': 'torn_cover_no_functional_loss_stated',
    'ALNST-020097-2024': 'broken_zipper_no_functional_loss_stated',
    'ALNST-020107-2024': 'canvas_visible_no_threshold',
    'ALNST-020239-2024': 'wear_no_threshold',
    'ALNST-020367-2024': 'outside_limit_stated',
    'ALNST-020380-2024': 'broken_zipper_no_functional_loss_stated',
}


def unit_scope(row, task, removals):
    """Exact identifiers support review but do not establish removed-unit role."""
    text = str(task['Task Description'])
    serial_hit = token_present(row['Serial #'], text)
    pn_hit = token_present(row['Part #'], text)
    candidates = removals[(removals['Aircraft #'] == row['Aircraft #']) &
                          (removals['Source Doc #'] == task['Execution Doc #'])]
    attached = candidates['Attached Serial #'].dropna()
    replacement_hit = any(token_present(s, text) for s in attached)
    if serial_hit and replacement_hit:
        return 'removed_and_installed_serials_present'
    if serial_hit:
        return 'removed_serial_present_role_requires_review'
    if replacement_hit:
        return 'installed_serial_present'
    return 'part_number_only' if pn_hit else 'component_family_only'


def review(audit, tasks, removals, catalog=None, unit_decisions=None):
    subset = audit[audit.category.isin(['condition_unspecified','no_component_diagnosis_within_3d'])]
    decisions, queue = [], []
    for _, row in subset.iterrows():
        docs = row.source_documents.split('|') if pd.notna(row.source_documents) else []
        context = tasks[(tasks['Aircraft #'] == row['Aircraft #']) &
                        tasks['Execution Doc #'].isin(docs) &
                        tasks['Task #'].str.contains('NST', na=False)]
        records = []
        for _, task in context.drop_duplicates(['Execution Doc #','Task #','Task Description']).iterrows():
            flags = screen(task['Task Description'], row['Part #'], row['Serial #'])
            plural_vest = row['Part #'].startswith('S-7200') and bool(
                re.search(r'\bvests\b|\blife jackets\b', str(task['Task Description']), re.I))
            if not flags['relevant'] and not plural_vest:
                continue
            scope = unit_scope(row, task, removals)
            text = str(task['Task Description'])
            digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
            diagnosis = (catalog.get((task['Task #'], digest), 'not_content_reviewed')
                         if catalog is not None else REVIEWED.get(task['Task #'], 'not_content_reviewed'))
            # Actual detector names are extracted as references, without deriving
            # a detection date from the administrative signoff date.
            detector = ('post_flight' if re.search(r'post.{0,2}flight|post.{0,2}fligth',text,re.I)
                        else 'inspection_unspecified' if re.search('inspect|insp',text,re.I)
                        else 'not_stated')
            lag = (task.d-row.rem).days if pd.notna(task.d) else float('nan')
            record = dict(audit_id=row.audit_id, pn=row['Part #'], serial=row['Serial #'],
                          aircraft=row['Aircraft #'], document=task['Execution Doc #'], task=task['Task #'],
                          source_sha256=digest,
                          signoff_lag_days=lag, unit_scope=scope, reviewed_description=diagnosis,
                          detector_reference=detector, detection_date_confirmed=False)
            decisions.append(record)
            records.append(record)
        reviewed = [r for r in records if r['reviewed_description'] != 'not_content_reviewed']
        if not records:
            state = 'no_relevant_diagnosis_in_source_document'
        elif not reviewed:
            state = 'retrieved_pending_content_review'
        else:
            state = 'description_reviewed_pending_unit_and_threshold'
        unit_review = next((r for r in records if unit_decisions is not None and
                            (row.audit_id, r['source_sha256']) in unit_decisions), None)
        if unit_review is not None:
            state = 'description_and_unit_reviewed_threshold_pending'
        queue.append(dict(audit_id=row.audit_id, pn=row['Part #'], serial=row['Serial #'],
                          aircraft=row['Aircraft #'], source_documents=row.source_documents,
                          previous_category=row.category, review_status=state,
                          retrieved_diagnoses=len(records), reviewed_diagnoses=len(reviewed),
                          retrieval_limit=('source_document_absent' if not tasks['Execution Doc #'].isin(docs).any()
                                           else 'source_document_present_no_matching_diagnosis' if not records else ''),
                          unit_confirmed=unit_review is not None, endpoint_confirmed=False))
    return pd.DataFrame(decisions), pd.DataFrame(queue)


def main():
    rows = pd.read_csv(DERIVED/'removal_label_audit.csv', parse_dates=['att','rem'])
    removals = pd.read_csv(DERIVED/'removals_clean.csv')
    source = pd.read_csv(ROOT/'analysis'/'removal_review_decisions.csv')
    catalog = {(r.task, r.source_sha256): r.description_decision for r in source.itertuples()}
    units = pd.read_csv(ROOT/'analysis'/'removal_unit_decisions.csv')
    unit_decisions = {(r.audit_id, r.source_sha256): r.unit_decision for r in units.itertuples()}
    decisions, queue = review(rows, load_omth(), removals, catalog=catalog, unit_decisions=unit_decisions)
    decisions.to_csv(DERIVED/'removal_review_evidence.csv', index=False)
    queue.to_csv(DERIVED/'removal_review_queue.csv', index=False)
    absent = queue[queue.retrieval_limit.eq('source_document_absent')].merge(
        rows[['audit_id','att','rem']], on='audit_id', validate='one_to_one')
    absent = absent[['audit_id','pn','serial','aircraft','att','rem','source_documents']]
    absent['needed_evidence'] = 'removed-unit identification; discrepancy; detection date and inspection; applicable threshold'
    absent.to_csv(DERIVED/'missing_source_documents.csv', index=False)
    counts = queue.review_status.value_counts().rename_axis('status').reset_index(name='removals')
    reviewed = decisions[decisions.reviewed_description != 'not_content_reviewed']
    codes = reviewed.groupby('reviewed_description').agg(
        tasks=('task','nunique'), removals=('audit_id','nunique')).reset_index()
    report = f'''# Revisão documental dos 315 registros inconclusivos

Execução: `py -3 analysis/removal_review.py`, após `removal_labels.py`.

## Procedimento

Recuperação no documento de origem e mesma aeronave, sem excluir assinaturas
pela tolerância de três dias. Mantém e contabiliza a defasagem administrativa.
Na recuperação, inclui as formas plurais de colete (`vests`, `life jackets`)
que a triagem anterior não reconhecia. A triagem original permanece preservada.
Revisão de conteúdo registrada em `analysis/removal_review_decisions.csv`;
o catálogo fixa tarefa, hash SHA-256 e decisão de leitura. O código somente
reaplica uma decisão se tarefa E hash coincidirem; textos alterados retornam
à pendência de revisão. O catálogo não é uma regra lexical de rotulagem física.
Não exporta descrições nem observações livres do operador.

## Cobertura

{counts.to_markdown(index=False)}

Descrições revisadas associadas a {reviewed.audit_id.nunique()} remoções;
{reviewed.task.nunique()} tarefas distintas. Categorias de conteúdo:

{codes.to_markdown(index=False)}

Limites de recuperação dos registros sem diagnóstico pertinente:

{queue.loc[queue.retrieved_diagnoses.eq(0), 'retrieval_limit'].value_counts().rename_axis('limitation').reset_index(name='removals').to_markdown(index=False)}

Escopo das referências nas evidências recuperadas (linhas de diagnóstico,
não uma partição das remoções):

{decisions.unit_scope.value_counts().rename_axis('scope').reset_index(name='evidence_rows').to_markdown(index=False)}

Uma remoção pode aparecer em mais de uma categoria/tarefa; não somar a tabela
como partição da população. Associação por família não confirma unidade.
Ausência de diagnóstico recuperado refere-se à busca em tarefas NST e ao
vocabulário empregado, não à prova de inexistência de informação no extrato.

## Achados e decisão

Foram encontrados desgaste sem limiar declarado, lona de pneu aparente, zíper
quebrado, dano de capa e retirada por conveniência de manutenção. Nenhum desses
termos isoladamente confirma falha funcional ou limite AMM excedido. Textos
somente de substituição/RII não identificam condição anterior à retirada.
Referências a P/N ou serial instalado são separadas de referência ao removido,
mas menção ao serial removido ainda exige verificar o papel no texto.

A fila mantém todos os 315 eventos. Nenhum é automaticamente recodificado como
falha, retirado da coorte ou convertido em censura independente. A revisão de
papel da unidade em `analysis/removal_unit_decisions.csv` sustenta a identidade
removida em {int(queue.unit_confirmed.sum())} registros: duas tesouras com
desgaste excessivo declarado e dois coletes com zíper quebrado. A evidência
de R&R de uma roda cita serial sem estabelecer seu papel, permanecendo ambígua.
As decisões exigem correspondência entre ID e hash do texto revisado.
Nenhum limiar de falha funcional foi confirmado; os demais registros também
permanecem com identidade de unidade a confirmar.
Datas de assinatura não são promovidas a datas de detecção; a referência a
pós-voo identifica somente o tipo de inspeção, sem inventar seu instante.

Próxima etapa: estabelecer, por registro, unidade removida, modo/limiar operacional
e data/inspeção do achado; recuperar os documentos faltantes e buscar evidência
adicional nos documentos presentes sem diagnóstico recuperado. Se o extrato
não contiver esses elementos, identificar a referência exata para recuperação
documental externa. A5 de remoções registradas permanece distinta de validação
de vida física para o contrafactual de substituição.

Artefatos: `data/derived/removal_review_evidence.csv` e `removal_review_queue.csv`.
Referências ausentes: `data/derived/missing_source_documents.csv`, com
{absent.source_documents.nunique()} documentos distintos para {len(absent)} remoções.
'''
    (ROOT/'analysis'/'removal_review_report.md').write_text(report, encoding='utf-8')
    print(counts.to_string(index=False))
    print('Content-reviewed removals:',reviewed.audit_id.nunique(), 'tasks:',reviewed.task.nunique())


if __name__ == '__main__':
    main()
