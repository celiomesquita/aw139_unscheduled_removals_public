# Emenda A16/A9_008 — MH de três P/N sem documento de remoção única

14/11/2026. Posterior a A16 corrigida e à errata de A5/A4, anterior a
qualquer réplica de piloto ou comparação de políticas A9/A10. O pré-registro
A16/A9 e as emendas 001–007 são preservados. Nenhuma simulação de política
foi usada para escolher estes coeficientes.

## Parada e autorização do autor

A conferência anterior ao piloto cumpriu a parada da seção 6: faltam documentos
de remoção única com MH para 3G6230A00833, 3G6230A00932 e 3G6430A00335.
O relatório analysis/a9_preflight_report.md e a tabela em
data/derived/a9/preflight/ preservam o diagnóstico anterior à autorização.

O autor escolheu explicitamente: “Preparar emenda para usar rateio, com
limitações e sensibilidades explícitas”. Esta emenda fixa essa aproximação;
não altera a fonte dos outros oito P/N nem os arquivos históricos de T4.

## Fonte e regra principal

Usar data/derived/single_removal_mh_summary.csv. Para os três P/N, somente,
selecionar aggregation=row_sum e cohort=all_equal_share: a mediana das MH
rateadas igualmente entre as remoções do documento. Não reinterpretar o rateio
como identificação causal do trabalho da peça ou como medida de preventiva.

| P/N | Documentos | Observações com MH | Mediana MH | Q1 | Q3 |
|---|---|---|---|---|---|
| 3G6230A00833 | 56 | 97 | 4,166666667 | 2,125 | 7,666666667 |
| 3G6230A00932 | 24 | 35 | 5 | 2,125 | 10,8125 |
| 3G6430A00335 | 23 | 37 | 3,75 | 1,5 | 7,5 |

Valores acima são arredondados para leitura; o cálculo usa os valores completos
do CSV congelado. Documentos e observações são contagens distintas, não réplicas
independentes. Para os outros oito P/N, manter aggregation=row_sum e
cohort=single_document, conferindo a correspondência com cost_parameters.csv.
Salvar tabela própria de A9, com fonte por P/N, contagens, quantis e hashes;
não preencher nem sobrescrever parâmetros históricos ausentes.

## Limitações e sensibilidades fixadas antes das políticas

O rateio pode atribuir tarefas independentes à remoção e diluir tarefas
específicas por várias peças. Pode tanto subestimar como superestimar a demanda
preventiva. Os oito coeficientes de documento único também não são medidas
causais de preventiva. A aproximação deve acompanhar todas as conclusões de
capacidade, viabilidade e custo; ela não valida carga de trabalho operacional.

Registrar quatro vetores de MH antes de comparar políticas:

1. Principal: medianas de soma de linhas, com a exceção acima para os três P/N.
2. Faixa inferior: Q1 das mesmas fontes por P/N.
3. Faixa superior: Q3 das mesmas fontes por P/N.
4. Agregação alternativa: medianas de task_max, mantendo exatamente a escolha
   single_document/all_equal_share de cada P/N.

Nenhum quantil ou agregação será escolhido pelo ganho de P2. As faixas não são
ICs nem extremos físicos. Em cada vetor, todas as políticas enfrentam as mesmas
MH e capacidade por visita igual à soma das MH das unidades ativas dividida
por quatro. A sensibilidade à capacidade metade/dobro prevista em A11 permanece
um eixo separado e explicitamente rotulado; não misturar mudança de demanda
com mudança de capacidade para atribuir causalidade a uma delas.

Se faltar valor finito positivo, fonte ou correspondência das contagens em
qualquer vetor, parar e informar; não usar zero nem substituir por outra peça.
Nenhum P/N é excluído e nenhum tamanho de grade é reduzido por esta emenda.

## Demais requisitos preservados

Os 11 P/N, parâmetros verdadeiros de A4 original, regra de exposição corrigida,
limiares 30/60, P0–P3, ablações, grade principal de 72 células e orçamento de
120 h continuam os mesmos. R ainda depende das cinco réplicas de piloto,
excluídas da inferência. A autorização desta aproximação não certifica o
simulador ou o MILP: testes de renovação, custo terminal, ótimo por enumeração,
uso somente do passado, capacidade, pareamento e determinismo precedem o piloto.
Não produzir comparações principais antes desses requisitos e do congelamento
da configuração, sementes e R. Esta emenda não solicita novo commit: a barreira
de commit dos protocolos anteriores já foi satisfeita, e a preparação desta
aproximação foi autorizada explicitamente pelo autor.
