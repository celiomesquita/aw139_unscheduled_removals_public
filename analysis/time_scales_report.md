# A2 — comparação exploratória de escalas de tempo

Gerado por `py -3 analysis/time_scales.py`, após `analysis/feasibility.py`.

## Protocolo

Coorte principal de instalações dentro da janela, entrada na idade zero.
Comparação pareada nas mesmas instalações para FH, calendário e decolagens.
AIC = 4 − 2 log L, usando a probabilidade do evento no intervalo diário
(dia anterior, remoção] e sobrevivência até a remoção nas censuras.
Assim, todas as verossimilhanças usam a mesma medida observacional, evitando
comparar densidades expressas em unidades diferentes. Relógios no fim do dia;
instalações e remoções no mesmo dia são excluídas por ordem desconhecida.
Nenhum contador ausente é imputado: trechos com registros de decolagem ausentes
entre instalação (exclusiva) e remoção são excluídos de todas as escalas.
Dias sem registros são tratados como sem voo, sujeito à completude do extrato.
Eventos sem exposição no último dia tornam a escala incompatível com este
protocolo; ficam sem ajuste, sem eliminar o evento ou inventar exposição.
Mínimo de 5 falhas após as exclusões. Mantém FH em empate;
alterna somente com melhoria de AIC ≥ 2 e convergência.

## Cobertura e resultados

| pn                    |   total |   retained |   events |   excluded |   invalid_dates |   missing_clock |   missing_cycles |
|:----------------------|--------:|-----------:|---------:|-----------:|----------------:|----------------:|-----------------:|
| 100-3010-000          |      10 |          2 |        1 |          8 |               0 |               0 |                8 |
| 1152546-2             |      90 |         13 |        7 |         77 |               0 |               0 |               77 |
| 1363A020001           |      18 |          4 |        3 |         14 |               0 |               0 |               14 |
| 2778-1                |      82 |         11 |        1 |         71 |               0 |               0 |               71 |
| 2922                  |      20 |          1 |        1 |         19 |               1 |               0 |               18 |
| 2966A010000           |      28 |          2 |        1 |         26 |               0 |               0 |               26 |
| 33204-002             |      57 |          5 |        1 |         52 |               1 |               0 |               51 |
| 3G2900V00652          |      18 |          3 |        2 |         15 |               1 |               0 |               14 |
| 3G3210V00333          |      14 |          6 |        4 |          8 |               0 |               0 |                8 |
| 3G3240A07431          |      85 |          9 |        3 |         76 |               1 |               0 |               75 |
| 3G3240A07531          |     241 |         48 |       28 |        193 |               0 |               0 |              193 |
| 3G3240V01731          |      64 |         27 |       22 |         37 |               1 |               0 |               36 |
| 3G6220A01252          |      75 |          3 |        0 |         72 |               0 |               0 |               72 |
| 3G6220V02051          |      81 |          4 |        1 |         77 |               0 |               0 |               77 |
| 3G6230A00833          |     108 |         16 |       10 |         92 |               0 |               0 |               92 |
| 3G6230A00932          |      37 |          4 |        1 |         33 |               0 |               0 |               33 |
| 3G6230A00934          |      20 |          0 |        0 |         20 |               0 |               0 |               20 |
| 3G6230A01133          |      47 |          1 |        1 |         46 |               1 |               0 |               45 |
| 3G6352V02452          |      31 |          3 |        1 |         28 |               0 |               0 |               28 |
| 3G6430A00335          |      56 |          2 |        1 |         54 |               0 |               0 |               54 |
| 500-12Y               |      15 |          4 |        2 |         11 |               3 |               0 |                8 |
| 500-32-2Y-S           |      17 |          5 |        3 |         12 |               2 |               0 |               10 |
| 7001840-934           |      16 |          4 |        3 |         12 |               0 |               0 |               12 |
| 7016683-966           |      17 |          5 |        5 |         12 |               0 |               0 |               12 |
| 7036340-802           |      36 |          7 |        4 |         29 |               0 |               0 |               29 |
| 7037620-814           |      41 |          9 |        4 |         32 |               1 |               0 |               31 |
| 8162-2                |     123 |         13 |        5 |        110 |               0 |               0 |              110 |
| 8486-3                |      21 |          2 |        0 |         19 |               1 |               0 |               18 |
| 940-0451-001          |       9 |          4 |        3 |          5 |               1 |               0 |                4 |
| M006-01H095-043       |      64 |          1 |        0 |         63 |               1 |               0 |               62 |
| S-7200-514-CREW-V/PLB |      45 |          2 |        0 |         43 |               2 |               0 |               41 |
| S-7200-514-PAX        |     303 |         39 |       19 |        264 |               1 |               0 |              263 |
| S-7200-514-PLB        |     240 |         28 |       23 |        212 |               1 |               0 |              211 |
| S-7200-517-PLB        |     119 |         15 |        4 |        104 |               0 |               0 |              104 |
| S-9450-14             |     203 |         28 |       14 |        175 |               2 |               0 |              173 |

| pn             | selected   |
|:---------------|:-----------|
| 1152546-2      | unresolved |
| 3G3240A07531   | unresolved |
| 3G3240V01731   | FH         |
| 3G6230A00833   | FH         |
| 7016683-966    | unresolved |
| 8162-2         | unresolved |
| S-7200-514-PAX | FH         |
| S-7200-514-PLB | unresolved |
| S-9450-14      | FH         |

## FH–calendário sem exigir contadores de ciclos

Mesma regra diária e mesma coorte dentro de cada comparação, mas sem excluir
trechos por decolagens ausentes. Cobertura e ajustes completos nos arquivos
`data/derived/time_scale_broad_*.csv`. A seleção permanece inconclusiva quando
FH atribui probabilidade zero a qualquer evento; não se escolhe calendário
automaticamente por esse motivo.

| pn                    |   total |   retained |   events |   excluded |   invalid_dates |   missing_clock |   missing_cycles |
|:----------------------|--------:|-----------:|---------:|-----------:|----------------:|----------------:|-----------------:|
| 100-3010-000          |      10 |         10 |        5 |          0 |               0 |               0 |                0 |
| 1152546-2             |      90 |         90 |       23 |          0 |               0 |               0 |                0 |
| 1363A020001           |      18 |         18 |        8 |          0 |               0 |               0 |                0 |
| 2778-1                |      82 |         82 |       10 |          0 |               0 |               0 |                0 |
| 2922                  |      20 |         19 |        4 |          1 |               1 |               0 |                0 |
| 2966A010000           |      28 |         28 |        9 |          0 |               0 |               0 |                0 |
| 33204-002             |      57 |         56 |       14 |          1 |               1 |               0 |                0 |
| 3G2900V00652          |      18 |         17 |        4 |          1 |               1 |               0 |                0 |
| 3G3210V00333          |      14 |         14 |        8 |          0 |               0 |               0 |                0 |
| 3G3240A07431          |      85 |         84 |        7 |          1 |               1 |               0 |                0 |
| 3G3240A07531          |     241 |        241 |      156 |          0 |               0 |               0 |                0 |
| 3G3240V01731          |      64 |         63 |       50 |          1 |               1 |               0 |                0 |
| 3G6220A01252          |      75 |         75 |       23 |          0 |               0 |               0 |                0 |
| 3G6220V02051          |      81 |         81 |       19 |          0 |               0 |               0 |                0 |
| 3G6230A00833          |     108 |        108 |       85 |          0 |               0 |               0 |                0 |
| 3G6230A00932          |      37 |         37 |       19 |          0 |               0 |               0 |                0 |
| 3G6230A00934          |      20 |         20 |       12 |          0 |               0 |               0 |                0 |
| 3G6230A01133          |      47 |         46 |        6 |          1 |               1 |               0 |                0 |
| 3G6352V02452          |      31 |         31 |       17 |          0 |               0 |               0 |                0 |
| 3G6430A00335          |      56 |         56 |       14 |          0 |               0 |               0 |                0 |
| 500-12Y               |      15 |         12 |        4 |          3 |               3 |               0 |                0 |
| 500-32-2Y-S           |      17 |         15 |        5 |          2 |               2 |               0 |                0 |
| 7001840-934           |      16 |         16 |        5 |          0 |               0 |               0 |                0 |
| 7016683-966           |      17 |         17 |        9 |          0 |               0 |               0 |                0 |
| 7036340-802           |      36 |         36 |       15 |          0 |               0 |               0 |                0 |
| 7037620-814           |      41 |         40 |       14 |          1 |               1 |               0 |                0 |
| 8162-2                |     123 |        123 |       15 |          0 |               0 |               0 |                0 |
| 8486-3                |      21 |         20 |        4 |          1 |               1 |               0 |                0 |
| 940-0451-001          |       9 |          8 |        4 |          1 |               1 |               0 |                0 |
| M006-01H095-043       |      64 |         63 |       28 |          1 |               1 |               0 |                0 |
| S-7200-514-CREW-V/PLB |      45 |         43 |       12 |          2 |               2 |               0 |                0 |
| S-7200-514-PAX        |     303 |        302 |       99 |          1 |               1 |               0 |                0 |
| S-7200-514-PLB        |     240 |        239 |      152 |          1 |               1 |               0 |                0 |
| S-7200-517-PLB        |     119 |        119 |        9 |          0 |               0 |               0 |                0 |
| S-9450-14             |     203 |        201 |       38 |          2 |               2 |               0 |                0 |

| pn                    | selected   |
|:----------------------|:-----------|
| 100-3010-000          | FH         |
| 1152546-2             | unresolved |
| 1363A020001           | unresolved |
| 2778-1                | unresolved |
| 2966A010000           | unresolved |
| 33204-002             | unresolved |
| 3G3210V00333          | unresolved |
| 3G3240A07431          | unresolved |
| 3G3240A07531          | unresolved |
| 3G3240V01731          | unresolved |
| 3G6220A01252          | unresolved |
| 3G6220V02051          | unresolved |
| 3G6230A00833          | unresolved |
| 3G6230A00932          | unresolved |
| 3G6230A00934          | unresolved |
| 3G6230A01133          | unresolved |
| 3G6352V02452          | unresolved |
| 3G6430A00335          | unresolved |
| 500-32-2Y-S           | unresolved |
| 7001840-934           | unresolved |
| 7016683-966           | unresolved |
| 7036340-802           | unresolved |
| 7037620-814           | unresolved |
| 8162-2                | unresolved |
| M006-01H095-043       | unresolved |
| S-7200-514-CREW-V/PLB | unresolved |
| S-7200-514-PAX        | unresolved |
| S-7200-514-PLB        | unresolved |
| S-7200-517-PLB        | unresolved |
| S-9450-14             | unresolved |

## Limites e próxima decisão

Resultados exploratórios, sem aprovação de K1 ou K2. A coorte completa pode
ser seletiva; avaliar os trechos excluídos antes de adoptar a escala. Decolagens
são proxy de ciclos, ainda sem validação como pousos. Achados em inspeção
continuam limitados ao último dia: A3 deve ampliar o intervalo para a última
inspeção pertinente. A escolha definitiva depende de A3 e da validação temporal
de A5. Não há inferência sobre economia ou eficácia de política.
