"""Full source-document review of the 26 previously unretrieved cases.

Replay explicit reading decisions only if the full source snapshot matches.
No text is exported and no operational event is relabelled as physical failure.
"""
import hashlib
import json

import pandas as pd

from feasibility import DERIVED, ROOT, load_omth

FIELDS = ['Task #', 'Task Description', 'Sign Off Remarks', 'Tech Sign Off Date']


def snapshot_hash(context):
    records = sorted(set(tuple(row) for row in context[FIELDS].fillna('').astype(str).to_numpy()))
    return hashlib.sha256(json.dumps(records, ensure_ascii=False).encode('utf-8')).hexdigest()


def validate_decisions(queue, tasks, catalog):
    rows = []
    for _, row in catalog.iterrows():
        case = queue[queue.audit_id.eq(row.audit_id)]
        if len(case) != 1:
            raise ValueError('Review case must match exactly one queue record')
        case = case.iloc[0]
        if case.source_documents != row.document or case.aircraft != row.aircraft:
            raise ValueError('Review source identity mismatch')
        context = tasks[tasks['Aircraft #'].eq(row.aircraft) & tasks['Execution Doc #'].eq(row.document)]
        current_hash = snapshot_hash(context)
        verified = bool(len(context) and current_hash == row.source_sha256)
        selected = context[context['Task #'].eq(row.evidence_task)]
        if row.evidence_task != 'FULL_DOCUMENT' and selected.empty:
            verified = False
        rows.append(dict(audit_id=row.audit_id, pn=case.pn, serial=case.serial,
                         aircraft=row.aircraft, document=row.document, evidence_task=row.evidence_task,
                         source_sha256=current_hash, source_rows=len(context),
                         review_status='source_review_completed' if verified else 'source_changed_review_required',
                         documentary_decision=row.documentary_decision if verified else 'unresolved',
                         detector_reference=row.detector_reference if verified else 'unresolved',
                         unit_confirmed=False, physical_failure_confirmed=False,
                         detection_date_confirmed=False))
    return pd.DataFrame(rows)


def main():
    queue = pd.read_csv(DERIVED/'removal_review_queue.csv')
    catalog = pd.read_csv(ROOT/'analysis'/'extended_review_decisions.csv')
    target = queue[queue.retrieval_limit.eq('source_document_present_no_matching_diagnosis')]
    if set(target.audit_id) != set(catalog.audit_id) or catalog.audit_id.duplicated().any():
        raise ValueError('Decision catalog must cover all 26 target cases exactly once')
    results = validate_decisions(queue, load_omth(), catalog)
    results.to_csv(DERIVED/'extended_review_results.csv', index=False)
    consolidated = queue[['audit_id','pn','serial','aircraft','source_documents',
                          'unit_confirmed','endpoint_confirmed','retrieval_limit']].copy()
    consolidated['content_reading_complete'] = queue.reviewed_diagnoses.gt(0)
    verified_ids = results.loc[results.review_status.eq('source_review_completed'),'audit_id']
    consolidated.loc[consolidated.audit_id.isin(verified_ids),'content_reading_complete'] = True
    consolidated['unresolved_reason'] = 'unit_identity_operational_threshold_and_detection_time'
    consolidated.loc[consolidated.unit_confirmed,'unresolved_reason'] = 'operational_threshold_and_detection_time'
    consolidated.loc[consolidated.retrieval_limit.eq('source_document_absent'),
                     'unresolved_reason'] = 'source_document_absent'
    consolidated.to_csv(DERIVED/'adjudication_status.csv',index=False)
    counts = results.documentary_decision.value_counts().rename_axis('decision').reset_index(name='removals')
    recovery = results[['audit_id','pn','serial','aircraft','document','evidence_task','documentary_decision']].copy()
    recovery['needed_evidence'] = 'removed-unit role; original discrepancy; operational threshold; detection date; previous negative inspection'
    recovery.to_csv(DERIVED/'present_document_evidence_gaps.csv', index=False)
    report = f'''# A3.1 — revisão integral dos 26 casos com documento presente

Execução: `py -3 analysis/extended_review.py`, após `removal_review.py`.

## Escopo e controle da evidência

Leitura das tarefas e observações do documento de origem, incluindo tarefas
programadas, discrepâncias NST e registros de reparo/RII. Sem filtro lexical ou
tolerância de assinatura para excluir linhas do documento. Decisões explícitas
em `analysis/extended_review_decisions.csv`; hash da coleção completa de
tarefa/descrição/observação/data impede reaplicar decisões a texto alterado.
Resultados satisfatórios após reparo não demonstram condição anterior sem falha.
Textos operacionais não são exportados.

## Resultado

{counts.to_markdown(index=False)}

Revisões com snapshot válido: {int(results.review_status.eq('source_review_completed').sum())}/{len(results)}.

{results[['audit_id','document','evidence_task','documentary_decision']].to_markdown(index=False)}

## Interpretação

Dois casos de tesouras têm referência a condição próxima do limite; três outros
documentam desgaste acima do limite permitido, mas sem identificar serial/posição
ou limiar numérico. Três substituições de tesouras aparecem nas observações de
uma discrepância de folga no swashplate; não se atribui automaticamente à tesoura
a condição de outro nível de montagem. Três remoções de parafusos aparecem em
contexto de substituição de amortecedor/terminal; a falha do parafuso não é
demonstrada. Cinco remoções de coletes têm somente inspeção programada com
resultado satisfatório, sem registrar a condição anterior por unidade.
Registros administrativos de correção não são eventos físicos novos confirmados.
Dois casos de roda têm relação de componente esclarecida pelas observações:
vazamento de válvula em pré-voo e desgaste excessivo em pós-voo; ainda sem serial
ou limiar físico confirmado. Nos quatro casos restantes não foi encontrada
evidência específica de tesoura no documento examinado.

Nenhum dos 26 casos confirma simultaneamente identidade da unidade removida,
limiar de falha funcional e instante de detecção. As referências às inspeções
são textuais; assinatura administrativa não é promovida a data do achado.
As decisões são por remoção, com documentos compartilhados; não constituem
26 observações documentais independentes. Nenhuma linha original foi alterada.

## Estado e próxima etapa

A leitura do conteúdo disponível dos 315 casos inicialmente inconclusivos está
encerrada: 271 pela recuperação anterior, 26 por esta revisão integral e 18
ligados a 12 documentos ausentes. Encerrar a leitura não aprova K1/K2 nem
conclui a confirmação física de A3.1. Quatro identidades foram sustentadas na
rodada anterior; os demais casos mantêm lacunas por unidade/limiar/data.
Os 18 casos ausentes permanecem em `missing_source_documents.csv`; os 26
casos com documento presente têm lacunas especificadas em `present_document_evidence_gaps.csv`.
Recuperar discrepância original, identificação da unidade, critério operacional,
data do achado e inspeção anterior pertinente antes de reconstruir A3.2.
Pode-se preparar A5 para remoções registradas, mas a lei de vida física necessária
ao contrafactual continua sem validação.
'''
    (ROOT/'analysis'/'extended_review_report.md').write_text(report, encoding='utf-8')
    print(counts.to_string(index=False))


if __name__ == '__main__':
    main()
