# A3.1 — revisão integral dos 26 casos com documento presente

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

| decision                                          |   removals |
|:--------------------------------------------------|-----------:|
| scheduled_inspection_no_unit_discrepancy          |          5 |
| no_component_specific_evidence                    |          4 |
| administrative_replacement_correction             |          3 |
| assembly_play_scissor_replacement_unit_unresolved |          3 |
| scissor_above_limit_stated_unit_unresolved        |          3 |
| near_limit_scissor_reference                      |          2 |
| associated_damper_replacement_not_bolt_failure    |          1 |
| damper_replacement_bolt_condition_unstated        |          1 |
| incorrect_component_removal_record_correction     |          1 |
| rod_end_wear_associated_bolt_replacement          |          1 |
| wheel_valve_leak_replacement_unit_unresolved      |          1 |
| wheel_excessive_wear_replacement_unit_unresolved  |          1 |

Revisões com snapshot válido: 26/26.

| audit_id   | document          | evidence_task     | documentary_decision                              |
|:-----------|:------------------|:------------------|:--------------------------------------------------|
| R00026     | ALTL-033556-2024  | FULL_DOCUMENT     | no_component_specific_evidence                    |
| R00027     | ALTL-033556-2024  | FULL_DOCUMENT     | no_component_specific_evidence                    |
| R00162     | ALHWO-003707-2024 | FULL_DOCUMENT     | no_component_specific_evidence                    |
| R00170     | ALHWO-003707-2024 | FULL_DOCUMENT     | no_component_specific_evidence                    |
| R00044     | ALTL-034671-2024  | ALNST-019341-2024 | associated_damper_replacement_not_bolt_failure    |
| R00078     | ALTL-035662-2024  | ALNST-019834-2024 | near_limit_scissor_reference                      |
| R00079     | ALTL-035662-2024  | ALNST-019834-2024 | near_limit_scissor_reference                      |
| R00165     | ALTL-037251-2024  | ALNST-020623-2024 | assembly_play_scissor_replacement_unit_unresolved |
| R00166     | ALTL-037251-2024  | ALNST-020623-2024 | assembly_play_scissor_replacement_unit_unresolved |
| R00172     | ALTL-037251-2024  | ALNST-020623-2024 | assembly_play_scissor_replacement_unit_unresolved |
| R00173     | ALTL-039606-2025  | ALNST-021862-2025 | administrative_replacement_correction             |
| R00293     | ALTL-041691-2025  | ALNST-023059-2025 | administrative_replacement_correction             |
| R00294     | ALTL-041691-2025  | ALNST-023059-2025 | administrative_replacement_correction             |
| R00298     | ALTL-041387-2025  | ALNST-022874-2025 | damper_replacement_bolt_condition_unstated        |
| R00328     | ALTL-040903-2025  | ALNST-022551-2025 | incorrect_component_removal_record_correction     |
| R00453     | ALHWO-004038-2025 | LIFE VEST INSP    | scheduled_inspection_no_unit_discrepancy          |
| R00454     | ALHWO-004038-2025 | LIFE VEST INSP    | scheduled_inspection_no_unit_discrepancy          |
| R00455     | ALHWO-004038-2025 | LIFE VEST INSP    | scheduled_inspection_no_unit_discrepancy          |
| R00456     | ALHWO-004038-2025 | LIFE VEST INSP    | scheduled_inspection_no_unit_discrepancy          |
| R00486     | ALHWO-004038-2025 | LIFE VEST INSP    | scheduled_inspection_no_unit_discrepancy          |
| R00537     | ALTL-043744-2025  | ALNST-024462-2025 | scissor_above_limit_stated_unit_unresolved        |
| R00540     | ALTL-043744-2025  | ALNST-024462-2025 | scissor_above_limit_stated_unit_unresolved        |
| R00550     | ALTL-043744-2025  | ALNST-024462-2025 | scissor_above_limit_stated_unit_unresolved        |
| R00572     | ALTL-043853-2025  | ALNST-024530-2025 | rod_end_wear_associated_bolt_replacement          |
| R00629     | ALTL-046753-2026  | ALNST-026410-2026 | wheel_valve_leak_replacement_unit_unresolved      |
| R00640     | ALTL-046409-2026  | ALNST-026137-2026 | wheel_excessive_wear_replacement_unit_unresolved  |

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
