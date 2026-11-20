"""Audit recorded endpoints for all primary-cohort wear-out candidates.

Document screening only: exports references and flags, not source free text.
No removal is relabelled or discarded by this screening.
"""
import re

import pandas as pd

from feasibility import DERIVED, ROOT, load_omth
from inspection_censoring import KEY

COMPONENTS = {
    '3G3240A07531': r'\btire\b|\btyre\b|\bwheel\b',
    '3G3240V01731': r'\btire\b|\btyre\b|\bwheel\b',
    'S-7200-514-PLB': r'\bvest\b|\blife jacket\b',
    'S-7200-514-PAX': r'\bvest\b|\blife jacket\b',
    '3G6230A00833': r'scissor', '3G6230A00932': r'scissor',
    '3G6230A00934': r'scissor', '3G6430A00335': r'scissor',
    'M006-01H095-043': r'rod.{0,5}end|damper',
    '3G6220A01252': r'damper.{0,20}bolt|bolt.{0,20}damper',
    '3G6220V02051': r'damper',
}
PATTERNS = {
    'margin': r'near.{0,15}limit|next to.{0,10}limit|close.{0,10}limit|on the limit',
    'exceeded': r'excessive|exessive|above.{0,15}limit|out of limit|beyond.{0,15}limit',
    'functional': r'\binoperative\b|not working|failed.{0,30}test|fail.{0,15}test|does not operate',
    'damage': r'\bdamag\w*|\bcorrosion\b|\bleak\w*|\bcrack\w*|\bworn\b',
}


def token_present(token, text):
    if pd.isna(token) or len(str(token).strip()) < 3:
        return False
    return bool(re.search(r'(?<![a-z0-9])'+re.escape(str(token).lower())+r'(?![a-z0-9])', text.lower()))


def screen(text, pn, serial):
    """Flags require component reference; source diagnosis only, never repair remarks."""
    text = str(text).lower()
    pn_ref, serial_ref = token_present(pn, text), token_present(serial, text)
    relevant = pn_ref or serial_ref or bool(re.search(COMPONENTS.get(pn, r'(?!)'), text))
    flags = {key: bool(relevant and re.search(pattern, text)) for key, pattern in PATTERNS.items()}
    return dict(relevant=relevant, pn_reference=pn_ref, serial_reference=serial_ref, **flags)


def category(flags):
    main = [k for k in ('margin','exceeded','functional') if flags[k]]
    if len(main) > 1:
        return 'mixed_document_evidence'
    if main:
        return main[0]+'_evidence'
    return 'damage_evidence' if flags['damage'] else 'condition_unspecified'


def audit(spells, removals, tasks, candidates):
    primary = spells[spells.source.eq('in_window_removed') & spells.event.eq(1) &
                     spells['Part #'].isin(candidates)].copy()
    primary = primary.reset_index(drop=True)
    primary['audit_id'] = ['R'+str(i+1).zfill(5) for i in primary.index]
    links = removals[KEY+['Source Doc #']].drop_duplicates()
    rows, evidence = [], []
    for _, row in primary.iterrows():
        hit = links
        for key in KEY:
            hit = hit[hit[key] == row[key]]
        docs = hit['Source Doc #'].dropna().unique()
        context = tasks[(tasks['Aircraft #'] == row['Aircraft #']) &
                        tasks['Execution Doc #'].isin(docs) &
                        tasks['Task #'].str.contains('NST', na=False) &
                        ((tasks.d-row.rem).abs().dt.days <= 3)]
        aggregate = {k: False for k in ('margin','exceeded','functional','damage')}
        matched = 0
        for _, task in context.drop_duplicates(['Execution Doc #','Task #','Task Description']).iterrows():
            flags = screen(task['Task Description'], row['Part #'], row['Serial #'])
            if not flags['relevant']:
                continue
            matched += 1
            aggregate = {k: aggregate[k] or flags[k] for k in aggregate}
            evidence.append(dict(audit_id=row.audit_id, document=task['Execution Doc #'],
                                 task=task['Task #'], signoff_date=task.d, **flags))
        state = category(aggregate) if matched else 'no_component_diagnosis_within_3d'
        if len(docs) != 1:
            state = 'ambiguous_or_missing_source_document'
        rows.append({k: row[k] for k in ['audit_id']+KEY} | dict(
            source_documents='|'.join(sorted(docs)), source_document_count=len(docs),
            relevant_diagnoses=matched, category=state, **aggregate))
    return pd.DataFrame(rows), pd.DataFrame(evidence)


def main():
    spells = pd.read_csv(DERIVED/'spells.csv', parse_dates=['att','rem'])
    removals = pd.read_csv(DERIVED/'removals_clean.csv', parse_dates=['att','rem'])
    models = pd.read_csv(DERIVED/'weibull_by_pn.csv')
    candidates = models.loc[models.regime.eq('wear-out'), 'pn']
    rows, evidence = audit(spells, removals, load_omth(), candidates)
    rows.to_csv(DERIVED/'removal_label_audit.csv', index=False)
    evidence.to_csv(DERIVED/'removal_label_evidence.csv', index=False)
    counts = rows.category.value_counts().rename_axis('category').reset_index(name='removals')
    summary = pd.crosstab(rows['Part #'], rows.category)
    summary.to_csv(DERIVED/'removal_label_summary.csv')
    report = f'''# Auditoria ampliada dos desfechos — A2/A3 e condição de A5

Execução: `py -3 analysis/removal_labels.py`, após a viabilidade.

## População e protocolo

Todos os {len(candidates)} P/N com IC de beta acima de 1 na viabilidade,
incluindo {len(rows)} remoções não programadas da coorte principal.
Vínculo por P/N, serial, aeronave, instalação e remoção; procura diagnóstico NST
na mesma aeronave e documento, assinatura dentro de ±3 dias. Referência ao
componente por P/N, serial ou vocabulário explícito em `COMPONENTS`.
Somente `Task Description` é usada para condição; resultados satisfatórios de
reparo não viram prova de ausência de falha. Dados originais não são alterados.
As classes são indícios documentais, não rótulos físicos confirmados.

## Resultados

{counts.to_markdown(index=False)}

{summary.to_markdown()}

## Regras, limites e decisão

Margem, limite excedido e indicação funcional concomitantes no mesmo documento
produzem classe mista. Dano/corrosão/vazamento é indício de condição, sem
pressupor perda funcional. Documento sem diagnóstico pertinente não constitui
evidência negativa. Vocabulário e tolerância são exploratórios e incompletos.
Mesmo P/N ou serial citado pode referir-se à unidade instalada; associação
por família pode referir-se a outra posição/unidade. Requer revisão por unidade,
modo e limiar; negações e condições compostas podem escapar às regras.
Não usar essa triagem automaticamente para excluir eventos, tratar retiradas
como censura independente, estimar taxa de falha funcional ou aprovar K1/K2.

A5 pode prever o endpoint operacional de remoção registrada, mas isso não
identifica a distribuição de vida física necessária ao contrafactual de A7–A9.
Próxima etapa: adjudicar diagnósticos mistos/ambíguos e recuperar a inspeção
detectora e datas de achado a partir dos documentos referenciados. Falhas
funcionais devem ter critério operacional explícito, não somente uma palavra.

Rastreabilidade sem texto livre: `removal_label_audit.csv`,
`removal_label_evidence.csv` e `removal_label_summary.csv` em `data/derived/`.
As contagens são por remoção, não por documento independente.
'''
    (ROOT/'analysis'/'removal_labels_report.md').write_text(report, encoding='utf-8')
    print(counts.to_string(index=False))
    print('Removals:',len(rows), 'P/N:',rows['Part #'].nunique())


if __name__ == '__main__':
    main()
