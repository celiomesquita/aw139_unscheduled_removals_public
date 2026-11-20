# T4 — coeficientes empíricos e parâmetros pendentes

Execução: `py -3 analysis/round2_costs.py`, após `event_costs.py`.

## Documento com uma remoção

Filtro conta TODAS as remoções no par aeronave/documento antes de selecionar a
única remoção não programada. Entram 1412 documentos, dos quais
1303 têm algum MH observado.
MH ausente não vira zero. As medianas, Q1 e Q3 por P/N, para soma de linhas e
soma dos máximos por tarefa, e a comparação com rateio igual estão em
`data/derived/single_removal_mh_summary.csv` (595 P/N).
Documento único reduz a ambiguidade entre remoções, mas pode conter tarefas
independentes. Não transforma seu total em MH causal da remoção. A6.1 permanece
sensibilidade; estes coeficientes são a fonte principal autorizada em T4.

## Retorno ao voo por episódio

| visit   | bound   |   total_episodes |   without_later_flight |   n_observed |   median |   q1 |   q3 |
|:--------|:--------|-----------------:|-----------------------:|-------------:|---------:|-----:|-----:|
| inside  | lower   |             1223 |                      4 |         1219 |        0 |    0 |    0 |
| inside  | upper   |             1223 |                      4 |         1219 |       48 |   48 |   48 |
| outside | lower   |             1107 |                     26 |         1081 |        0 |    0 |    0 |
| outside | upper   |             1107 |                     26 |         1081 |       48 |   48 |   96 |

Fora − dentro: diferença das medianas dos limites inferiores =
0.000 h;
diferença das medianas dos limites superiores =
0.000 h.
Faixa de contraste por extremos: [-48.000, 48.000] h; ponto central descritivo
0.000 h. Não é IC estatístico nem efeito causal. Usa os mesmos episódios
com voo posterior para os dois limites; episódios sem voo posterior ficam nas
contagens de cobertura. Diferenças não positivas não são truncadas para fabricar
uma penalidade favorável. Coocorrência com visita segue o proxy de A6.

## Coeficientes e dupla contagem

`config/cost_parameters.csv`: esquema parametro, valor_central, faixa_min,
faixa_max, fonte. Dados empíricos têm fonte dados; faixa de MH/preço/gap por
grupo é IQR, enquanto a faixa do contraste usa extremos de medianas.
Taxa horária e custo de oportunidade por aeronave-dia: AUTOR_DEFINIR.
Não há conversão monetária nem objetivo executado.

Na representação com tempo total do episódio, o termo de oportunidade será
custo_dia × gap_horas/24. A diferença fora−dentro é DIAGNÓSTICA e NÃO é somada
novamente como penalidade temporal. Alternativa de decomposição: tempo de visita
mais incremento fora de visita, substituindo o tempo total, nunca acumulando as
duas representações. Penalidade adicional fixa exigiria evidência de custo
distinto (mobilização etc.), ausente; nenhum valor foi inventado.

T4 concluída com coeficientes empíricos e duas decisões do autor pendentes.
A6 permanece parcial até essas definições; isso não bloqueia A5.
