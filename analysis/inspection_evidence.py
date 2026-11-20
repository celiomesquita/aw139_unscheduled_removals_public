"""A3 documentary audit of proposed scissor inspection intervals.

Export rule identifiers and source references, never operational free text.
Flags describe evidence strength, not automated confirmation of failure.
"""
import re

import pandas as pd

from feasibility import DERIVED, ROOT, load_omth

COMPONENT = r'scissor'
MARGIN = r'near.{0,15}limit|next to.{0,10}limit|close.{0,10}limit|on the limit'
EXCEEDED = r'excessive|exessive|above.{0,15}limit|out of limit'
DETECTION = r'was found|was detected|were found|detected|found'


def description_flags(texts, task):
    """Require the component and condition in the same description."""
    relevant = [str(t).lower() for t in texts if re.search(COMPONENT, str(t), re.I)]
    findings = [t for t in relevant if re.search(DETECTION, t)]
    return dict(component_finding=bool(findings),
                margin_replacement=any(re.search(MARGIN, t) for t in findings),
                exceeded_limit=any(re.search(EXCEEDED, t) for t in findings),
                named_detection=any(task.lower() in t and re.search(DETECTION, t)
                                    for t in findings))


def audit(intervals, tasks):
    rows = []
    for _, row in intervals[intervals.interval_event].iterrows():
        task = row.inspection_task
        current = tasks[(tasks['Aircraft #'] == row['Aircraft #']) &
                        (tasks['Execution Doc #'] == row['Source Doc #'])]
        current_flags = description_flags(current['Task Description'], task)
        prior = tasks[(tasks['Aircraft #'] == row['Aircraft #']) &
                      (tasks['Task #'] == task) & (tasks.d == row.lower_date)]
        prior_docs = sorted(prior['Execution Doc #'].dropna().unique())
        prior_context = tasks[(tasks['Aircraft #'] == row['Aircraft #']) &
                              tasks['Execution Doc #'].isin(prior_docs)]
        previous_flags = description_flags(prior_context['Task Description'], task)
        remarks = prior['Sign Off Remarks'].fillna('').str.lower()
        satisfactory = remarks.str.contains(r'\bsatisfactory result|\bno defect|\bno discrepanc', regex=True).any()
        negative_proxy = bool(satisfactory and not previous_flags['component_finding'])
        if current_flags['margin_replacement']:
            verdict = 'preventive_margin_not_confirmed_failure'
        elif not current_flags['named_detection']:
            verdict = 'detection_by_different_or_unspecified_inspection'
        elif not negative_proxy:
            verdict = 'previous_negative_not_supported'
        elif not current_flags['exceeded_limit']:
            verdict = 'failure_threshold_not_supported'
        else:
            verdict = 'document_supported_candidate_requires_unit_mode_review'
        rows.append({k: row[k] for k in ['Part #','Serial #','Aircraft #','att','rem',
                                         'Source Doc #','lower_date','inspection_task']} | {
            'previous_documents': '|'.join(prior_docs),
            'previous_satisfactory': bool(satisfactory),
            'previous_component_finding': previous_flags['component_finding'],
            'previous_negative_proxy': negative_proxy, **current_flags, 'verdict': verdict})
    return pd.DataFrame(rows)


def main():
    intervals = pd.read_csv(DERIVED/'inspection_intervals.csv',
                            parse_dates=['att','rem','lower_date'])
    evidence = audit(intervals, load_omth())
    evidence.to_csv(DERIVED/'inspection_evidence.csv', index=False)
    counts = evidence.verdict.value_counts().rename_axis('verdict').reset_index(name='events')
    report = f'''# A3 — validação documental dos intervalos propostos

Execução: `py -3 analysis/inspection_evidence.py`, após `inspection_censoring.py`.

## Regras e rastreabilidade

Auditoria das dez propostas de intervalo de tesouras. Pesquisa na descrição da
discrepância no documento atual: componente, detecção, tarefa nominal e condição
próxima/no limite versus limite excedido. Os indicadores devem coexistir na
mesma descrição de componente; não se usa o resultado satisfatório de uma
substituição como prova da condição anterior. A inspeção prévia precisa registrar
resultado satisfatório; documentos com achados de tesouras não sustentam o proxy
de inspeção negativa. Datas recuperadas por mediana do documento mantêm a
limitação da extração OMTH. Regras explícitas em `description_flags` e `audit`.

## Resultado

{counts.to_markdown(index=False)}

Inspeção anterior com resultado satisfatório: {int(evidence.previous_satisfactory.sum())}/10.
Proxy de inspeção anterior negativa, sem achado de tesoura no documento:
{int(evidence.previous_negative_proxy.sum())}/10.
Detecção menciona nominalmente a tarefa proposta: {int(evidence.named_detection.sum())}/10.
Descrição menciona substituição próxima/no limite: {int(evidence.margin_replacement.sum())}/10.
Descrição menciona limite excedido: {int(evidence.exceeded_limit.sum())}/10.

## Consequência científica

O rótulo UNSCHEDULED não equivale automaticamente a falha: pode incluir retirada
por margem preventiva. A coincidência documental não identifica a inspeção
detectora. A sensibilidade Weibull anterior continua reproduzível, mas não
confirma desgaste de um modo de falha fisicamente definido nem aprova K1.
Antes de A5, definir o endpoint (remoção não programada versus falha funcional)
e auditar os rótulos da coorte. Se o endpoint for remoção, os parâmetros descrevem
o processo de remoção sob a política observada; não são automaticamente uma lei
de vida física transferível ao contrafactual de substituição preventiva.
Revisão de unidade e modo de falha continua necessária mesmo para candidatos
com suporte documental; expressões regulares não constituem validação física.

Evidência por trecho e referências documentais: `data/derived/inspection_evidence.csv`.
Nenhum texto livre ou nome de funcionário é exportado.
'''
    (ROOT/'analysis'/'inspection_evidence_report.md').write_text(report, encoding='utf-8')
    print(counts.to_string(index=False))


if __name__ == '__main__':
    main()
