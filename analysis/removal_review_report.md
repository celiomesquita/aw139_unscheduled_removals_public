# Revisão documental dos 315 registros inconclusivos

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

| status                                          |   removals |
|:------------------------------------------------|-----------:|
| description_reviewed_pending_unit_and_threshold |        267 |
| no_relevant_diagnosis_in_source_document        |         44 |
| description_and_unit_reviewed_threshold_pending |          4 |

Descrições revisadas associadas a 271 remoções;
190 tarefas distintas. Categorias de conteúdo:

| reviewed_description                         |   tasks |   removals |
|:---------------------------------------------|--------:|-----------:|
| broken_zipper_no_functional_loss_stated      |       3 |          3 |
| canvas_visible_no_threshold                  |       5 |          6 |
| ceramic_condition_no_functional_loss_stated  |       4 |          6 |
| damage_no_functional_loss_stated             |      24 |         60 |
| excess_or_limit_statement_requires_threshold |       8 |         15 |
| excessive_wear_stated                        |       1 |          2 |
| maintenance_convenience                      |       1 |          1 |
| near_limit                                   |       2 |          5 |
| outside_limit_stated                         |       1 |          2 |
| play_no_threshold                            |       3 |          6 |
| poor_condition_no_threshold                  |      14 |         25 |
| replacement_or_rii_only                      |      11 |         19 |
| scheduled_threshold_or_inspection_reference  |       3 |          5 |
| scratched_no_functional_loss_stated          |       5 |          7 |
| torn_cover_no_functional_loss_stated         |       1 |          3 |
| uneven_wear_no_threshold                     |       1 |          1 |
| wear_no_threshold                            |     103 |        114 |

Limites de recuperação dos registros sem diagnóstico pertinente:

| limitation                                    |   removals |
|:----------------------------------------------|-----------:|
| source_document_present_no_matching_diagnosis |         26 |
| source_document_absent                        |         18 |

Escopo das referências nas evidências recuperadas (linhas de diagnóstico,
não uma partição das remoções):

| scope                                       |   evidence_rows |
|:--------------------------------------------|----------------:|
| component_family_only                       |             270 |
| removed_serial_present_role_requires_review |               5 |
| part_number_only                            |               5 |

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
removida em 4 registros: duas tesouras com
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
12 documentos distintos para 18 remoções.
