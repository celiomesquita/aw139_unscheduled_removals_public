# A6.1 — atribuição exploratória de homem-hora por tarefa

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

| status                      |   removals |
|:----------------------------|-----------:|
| no_candidate_task           |       5691 |
| provisional_task_allocation |       1211 |
| candidate_tasks_missing_mh  |        401 |

| basis                      |   task_removal_links |
|:---------------------------|---------------------:|
| component_family_reference |                 1241 |
| removed_serial_reference   |                  421 |
| part_number_reference      |                  146 |
| installed_serial_reference |                   10 |

## Conservação contábil nas tarefas dos documentos ligados

| aggregation   |   observed_mh |   candidate_allocated_mh |   unallocated_mh |
|:--------------|--------------:|-------------------------:|-----------------:|
| row_sum       |       63183.8 |                   3804.9 |          59378.8 |
| max           |       41362.6 |                   2670.1 |          38692.5 |

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
