# T2 — A3 ampliada e decisão K1

Desfecho: remoção não programada registrada (T1), não falha física confirmada.
Regra fixada em `tarefas_codex.md`: IC de beta acima de 1 na versão exata e
na versão intervalar com mapa; K1 favorável com pelo menos cinco P/N retidos.

## Mapa e observação

`config/rotor_inspection_map.csv` fixa tarefa/P/N e motivo em códigos. Seleciona
tarefas periódicas específicas de amortecedor e tesouras/cabeça do rotor principal
de `recurrent_tasks.csv`. Não presume que inspeções genéricas de célula observem
esse conjunto. O mapa amplo representa uma aproximação operacional compartilhada
entre componentes da cabeça; não comprova detectabilidade de cada modo físico.
Inclui os seis candidatos ATA 62, inclusive parafuso e terminal. Usa a última
execução anterior à remoção na mesma aeronave, independentemente do documento,
sem ultrapassar a instalação. Sem execução anterior na instalação: limite zero.
Exposição FH nula: exclusão idêntica nas três versões, quantificada na tabela.
Última inspeção com mesma exposição FH da remoção: intervalo não identificável,
evento conservado como exato na versão com mapa, sem inventar exposição positiva.
Genérica: (max(0, idade−86.75 FH), idade].
Fora do ATA 62 (incluindo tesoura de cauda ATA 64), mantém eventos exatos porque
o mapa de cabeça do rotor principal não se aplica. Censuras conservam a exposição
integral. Coorte principal, entrada em idade zero; sem extrapolação pré-2024.

## Ajustes

| pn              |   ata | version   |   spells |   events |   intervals |   zero_exposure_excluded |   beta |      eta |   beta_lo |   beta_hi | converged   |
|:----------------|------:|:----------|---------:|---------:|------------:|-------------------------:|-------:|---------:|----------:|----------:|:------------|
| 3G3240A07531    |  3200 | exact     |      239 |      156 |           0 |                        2 | 1.3401 |  342.777 |    1.21   |    1.4841 | True        |
| 3G3240A07531    |  3200 | mapped    |      239 |      156 |           0 |                        2 | 1.3401 |  342.777 |    1.21   |    1.4841 | True        |
| 3G3240A07531    |  3200 | generic   |      239 |      156 |           0 |                        2 | 1.3401 |  342.777 |    1.21   |    1.4841 | True        |
| 3G3240V01731    |  3200 | exact     |       62 |       50 |           0 |                        2 | 1.4069 |  265.095 |    1.1809 |    1.6762 | True        |
| 3G3240V01731    |  3200 | mapped    |       62 |       50 |           0 |                        2 | 1.4069 |  265.095 |    1.1809 |    1.6762 | True        |
| 3G3240V01731    |  3200 | generic   |       62 |       50 |           0 |                        2 | 1.4069 |  265.095 |    1.1809 |    1.6762 | True        |
| 3G6220A01252    |  6200 | exact     |       75 |       23 |           0 |                        0 | 1.8474 | 1491.02  |    1.3582 |    2.5129 | True        |
| 3G6220A01252    |  6200 | mapped    |       75 |       23 |          20 |                        0 | 1.8209 | 1490.72  |    1.3376 |    2.4789 | True        |
| 3G6220A01252    |  6200 | generic   |       75 |       23 |          23 |                        0 | 1.6953 | 1512.95  |    1.2369 |    2.3236 | True        |
| 3G6220V02051    |  6200 | exact     |       81 |       19 |           0 |                        0 | 2.2286 | 2146.02  |    1.5946 |    3.1145 | True        |
| 3G6220V02051    |  6200 | mapped    |       81 |       19 |          19 |                        0 | 2.1859 | 2155.87  |    1.5629 |    3.0574 | True        |
| 3G6220V02051    |  6200 | generic   |       81 |       19 |          19 |                        0 | 2.1058 | 2171.55  |    1.5021 |    2.9522 | True        |
| 3G6230A00833    |  6200 | exact     |      106 |       85 |           0 |                        2 | 3.0852 |  330.303 |    2.6889 |    3.5399 | True        |
| 3G6230A00833    |  6200 | mapped    |      106 |       85 |          85 |                        2 | 2.9858 |  316.881 |    2.6012 |    3.4272 | True        |
| 3G6230A00833    |  6200 | generic   |      106 |       85 |          85 |                        2 | 2.7994 |  285.76  |    2.4151 |    3.2447 | True        |
| 3G6230A00932    |  6200 | exact     |       37 |       19 |           0 |                        0 | 1.9401 |  827.853 |    1.3492 |    2.7897 | True        |
| 3G6230A00932    |  6200 | mapped    |       37 |       19 |          19 |                        0 | 1.8815 |  817.265 |    1.3076 |    2.7073 | True        |
| 3G6230A00932    |  6200 | generic   |       37 |       19 |          19 |                        0 | 1.7369 |  797.244 |    1.1954 |    2.5238 | True        |
| 3G6230A00934    |  6200 | exact     |       20 |       12 |           0 |                        0 | 2.4502 | 1256.15  |    1.5943 |    3.7657 | True        |
| 3G6230A00934    |  6200 | mapped    |       20 |       12 |          12 |                        0 | 2.38   | 1248.91  |    1.5436 |    3.6695 | True        |
| 3G6230A00934    |  6200 | generic   |       20 |       12 |          12 |                        0 | 2.3156 | 1228.08  |    1.4941 |    3.5888 | True        |
| 3G6430A00335    |  6400 | exact     |       56 |       14 |           0 |                        0 | 1.6725 | 2219.61  |    1.0789 |    2.5926 | True        |
| 3G6430A00335    |  6400 | mapped    |       56 |       14 |           0 |                        0 | 1.6725 | 2219.61  |    1.0789 |    2.5926 | True        |
| 3G6430A00335    |  6400 | generic   |       56 |       14 |           0 |                        0 | 1.6725 | 2219.61  |    1.0789 |    2.5926 | True        |
| M006-01H095-043 |  6200 | exact     |       62 |       28 |           0 |                        2 | 2.166  | 1298.81  |    1.6536 |    2.8371 | True        |
| M006-01H095-043 |  6200 | mapped    |       62 |       28 |          27 |                        2 | 2.1423 | 1291.39  |    1.6353 |    2.8065 | True        |
| M006-01H095-043 |  6200 | generic   |       62 |       28 |          28 |                        2 | 2.0321 | 1278.66  |    1.5472 |    2.669  | True        |
| S-7200-514-PAX  |  2500 | exact     |      302 |       99 |           0 |                        1 | 1.3113 | 1039.12  |    1.1216 |    1.5331 | True        |
| S-7200-514-PAX  |  2500 | mapped    |      302 |       99 |           0 |                        1 | 1.3113 | 1039.12  |    1.1216 |    1.5331 | True        |
| S-7200-514-PAX  |  2500 | generic   |      302 |       99 |           0 |                        1 | 1.3113 | 1039.12  |    1.1216 |    1.5331 | True        |
| S-7200-514-PLB  |  2500 | exact     |      239 |      152 |           0 |                        1 | 1.2511 |  444.184 |    1.1079 |    1.4128 | True        |
| S-7200-514-PLB  |  2500 | mapped    |      239 |      152 |           0 |                        1 | 1.2511 |  444.184 |    1.1079 |    1.4128 | True        |
| S-7200-514-PLB  |  2500 | generic   |      239 |      152 |           0 |                        1 | 1.2511 |  444.184 |    1.1079 |    1.4128 | True        |

IC 95% Wald em log beta, ainda sem correção por dependência entre trechos da
mesma aeronave. Bootstrap por aeronave não executado nesta rodada (opcional).
Não comparar AIC entre versões com observações exatas e intervalares.

## Decisão

**K1 favorável: 11 de 11 P/N retidos.**

| pn              | retained   |   exact_beta_lo |   mapped_beta_lo |
|:----------------|:-----------|----------------:|-----------------:|
| 3G3240A07531    | True       |          1.21   |           1.21   |
| 3G3240V01731    | True       |          1.1809 |           1.1809 |
| 3G6220A01252    | True       |          1.3582 |           1.3376 |
| 3G6220V02051    | True       |          1.5946 |           1.5629 |
| 3G6230A00833    | True       |          2.6889 |           2.6012 |
| 3G6230A00932    | True       |          1.3492 |           1.3076 |
| 3G6230A00934    | True       |          1.5943 |           1.5436 |
| 3G6430A00335    | True       |          1.0789 |           1.0789 |
| M006-01H095-043 | True       |          1.6536 |           1.6353 |
| S-7200-514-PAX  | True       |          1.1216 |           1.1216 |
| S-7200-514-PLB  | True       |          1.1079 |           1.1079 |

A decisão é sobre padrão de idade no processo de remoção, sob o mapa operacional
assumido. Não confirma desgaste físico nem eficácia de política. K2 ainda não
avaliado; sobrevivência e seleção temporal de escala serão examinadas em A5.
