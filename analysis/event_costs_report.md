# A6 — evidências para custo e retorno ao voo

Execução: `py -3 analysis/event_costs.py`, após `analysis/feasibility.py`.

## Cobertura observada

| quantity                                |   value |
|:----------------------------------------|--------:|
| Removals                                |    7303 |
| Unscheduled removals                    |    4421 |
| Linked removals                         |    6678 |
| Linked unscheduled removals             |    3963 |
| Linked documents                        |    3327 |
| Linked documents with some missing MH   |     320 |
| Unscheduled aircraft-day episodes       |    2330 |
| Episodes with flight on removal day     |    1697 |
| Episodes without later flight in window |      30 |

| inside_visit_proxy   |   removals |   median_catalogue_cost |   median_mh_row_share |   median_mh_task_max_share |
|:---------------------|-----------:|------------------------:|----------------------:|---------------------------:|
| outside              |       2092 |                 2041.78 |                  5.62 |                       4    |
| inside               |       2286 |                 1351    |                  5    |                       3.95 |
| unknown              |         43 |                19249    |                nan    |                     nan    |

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
remoção: 48.0 h de
limite superior mediano, sob datas sem horário. Com diferença de k dias, a faixa
é [max(0,k−1),k+1] × 24 h; voo no dia da remoção impõe limite inferior zero, pois
a ordem é desconhecida. Sem voo posterior, o fim da janela limita a observação;
voo no mesmo dia impede afirmar censura à direita da verdadeira duração.
Limites pressupõem extrato de voos completo; não imputam voos não registrados.

Esses intervalos são proxies do retorno ao voo, não indisponibilidade causal:
demanda operacional, outras tarefas e esperas podem determinar a próxima saída.
Visitas usam as janelas da viabilidade com tolerância de ±2 dias;
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
