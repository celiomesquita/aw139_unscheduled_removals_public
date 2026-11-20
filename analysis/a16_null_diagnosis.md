# T13 — diagnóstico dos controles nulos de A16

Análise exploratória posterior à parada, usando somente artefatos salvos e relógios registrados. Nenhum modelo foi ajustado e nenhuma previsão foi corrigida. A decisão original de parada e os 600 controles permanecem preservados; a exclusão abaixo é diagnóstico, sem regra de decisão substituta.

## Agregado original e exclusão AC-22/2025-12-01

| cell    | variant     |   n |   original_mean |   empirical_sd |   bootstrap_se_mean |   excluded_mean |   original_positive_lo |   diagnostic_positive_lo |   excluded_rows |
|:--------|:------------|----:|----------------:|---------------:|--------------------:|----------------:|-----------------------:|-------------------------:|----------------:|
| null_x1 | principal   | 200 |      0.00542769 |     0.00509043 |          0.00611331 |     -0.00150078 |                      0 |                        0 |            1200 |
| null_x1 | realized_fh | 200 |     -0.00171766 |     0.00102005 |          0.00096412 |     -0.00178373 |                      0 |                        0 |            1200 |
| null_x2 | principal   | 200 |      0.00542137 |     0.00358114 |          0.00508371 |     -0.00149142 |                      0 |                        0 |            2400 |
| null_x2 | realized_fh | 200 |     -0.00162840 |     0.00068448 |          0.00067310 |     -0.00171125 |                      0 |                        0 |            2400 |
| null_x4 | principal   | 200 |      0.00631671 |     0.00284558 |          0.00430006 |     -0.00158623 |                     30 |                        0 |            4800 |
| null_x4 | realized_fh | 199 |     -0.00165497 |     0.00049370 |          0.00049838 |     -0.00178711 |                      0 |                        0 |            4776 |

Mesma agregação aeronave → origem → horizonte e bootstrap PCG64/20261112, B=999, universo original de 24/48/96 códigos e Bonferroni para 11 P/N. Excluem-se todas as linhas AC-22/2025-12-01 e suas cópias, mantendo o universo de reamostragem. Contagens com limite inferior positivo são descritivas; não reclassificam a barreira. Uma variante original falhou (null_x4, réplica 187, realized_fh, PermissionError em heartbeat); ela não foi reestimada ou substituída.

## Diferença por P/N e contribuições

| cell    | variant     | pn           |        mean |        std |   count |
|:--------|:------------|:-------------|------------:|-----------:|--------:|
| null_x1 | principal   | 3G3240V01731 |  0.02824883 | 0.02789247 |     200 |
| null_x1 | realized_fh | 3G3240V01731 | -0.01034115 | 0.00895401 |     200 |
| null_x2 | principal   | 3G3240V01731 |  0.02853560 | 0.01977333 |     200 |
| null_x2 | realized_fh | 3G3240V01731 | -0.00984045 | 0.00638203 |     200 |
| null_x4 | principal   | 3G3240V01731 |  0.03246314 | 0.01553024 |     200 |
| null_x4 | realized_fh | 3G3240V01731 | -0.01146878 | 0.00527643 |     199 |

pn_deltas.csv contém todos os P/N por réplica. pn_aircraft_origin.csv decompõe cada P/N por aeronave/cópia × origem, com contribuição normalizada pela agregação original. aggregate_aircraft_origin.csv faz a decomposição do agregado sem confundir pesos de P/N com pesos de aeronave. As tabelas guardam média, desvio e quantidade de réplicas presentes.

| cell    | variant     |   delta_mean |   contribution_mean |
|:--------|:------------|-------------:|--------------------:|
| null_x1 | principal   |   0.30485265 |          0.03810658 |
| null_x1 | realized_fh |   0.00290702 |          0.00036338 |
| null_x2 | principal   |   0.30416298 |          0.01901019 |
| null_x2 | realized_fh |   0.00364516 |          0.00022782 |
| null_x4 | principal   |   0.34772952 |          0.01086655 |
| null_x4 | realized_fh |   0.00581441 |          0.00018170 |

## AC-22, dezembro: probabilidades originais

| cell    | variant     |   horizon |   observed |        hW |        hE |
|:--------|:------------|----------:|-----------:|----------:|----------:|
| null_x1 | principal   |         1 |  0.3600000 | 0.0042246 | 0.0022173 |
| null_x1 | principal   |         2 |  0.5525000 | 0.0081750 | 0.0044009 |
| null_x1 | principal   |         3 |  0.6200000 | 0.0115647 | 0.0063449 |
| null_x1 | realized_fh |         1 |  0.3600000 | 0.3359581 | 0.2948864 |
| null_x1 | realized_fh |         2 |  0.5525000 | 0.5409866 | 0.5249620 |
| null_x1 | realized_fh |         3 |  0.6200000 | 0.6432022 | 0.6450222 |
| null_x2 | principal   |         1 |  0.3650000 | 0.0041832 | 0.0022202 |
| null_x2 | principal   |         2 |  0.5687500 | 0.0081102 | 0.0044075 |
| null_x2 | principal   |         3 |  0.6150000 | 0.0114857 | 0.0063553 |
| null_x2 | realized_fh |         1 |  0.3650000 | 0.3357856 | 0.2954434 |
| null_x2 | realized_fh |         2 |  0.5687500 | 0.5408929 | 0.5262356 |
| null_x2 | realized_fh |         3 |  0.6150000 | 0.6431849 | 0.6467221 |
| null_x4 | principal   |         1 |  0.3837500 | 0.0043841 | 0.0022300 |
| null_x4 | principal   |         2 |  0.5912500 | 0.0084933 | 0.0044269 |
| null_x4 | principal   |         3 |  0.6443750 | 0.0120184 | 0.0063832 |
| null_x4 | realized_fh |         1 |  0.3844221 | 0.3405963 | 0.2966801 |
| null_x4 | realized_fh |         2 |  0.5910804 | 0.5440779 | 0.5281144 |
| null_x4 | realized_fh |         3 |  0.6444724 | 0.6449930 | 0.6487440 |

Médias entre réplicas para o P/N 3G3240V01731 e as cópias de AC-22, na origem 2025-12-01. Não são probabilidades da regra corrigida.

## B=999 versus B=10 000

| variant     |   n |   reject999 |   reject10000 |   changed |
|:------------|----:|------------:|--------------:|----------:|
| principal   |  20 |           3 |             3 |         0 |
| realized_fh |  20 |           0 |             0 |         0 |

Réplicas fixadas 0–19 de null_x4, ambas as variantes. O recálculo B=999 reproduz exatamente os intervalos originais, inclusive por P/N. bootstrap_comparison.csv guarda todos os limites e classificações, não somente o agregado.

## Inventário de cobertura nos dados reais

| aircraft   | origin     | window_start   | window_end_exclusive   | first_record   | last_record   |   observed_days | incomplete_window   |   risk_units |   FH_risk_units | coverage_kind    | has_record_after_origin   |   legacy_rate_FH |   legacy_rate_takeoffs |
|:-----------|:-----------|:---------------|:-----------------------|:---------------|:--------------|----------------:|:--------------------|-------------:|----------------:|:-----------------|:--------------------------|-----------------:|-----------------------:|
| AC-22      | 2025-12-01 | 2025-09-02     | 2025-12-01             | 2025-11-15     | 2026-03-31    |              16 | True                |            2 |               2 | partial_positive | True                      |        0.0244444 |              0.0555556 |

| aircraft   | origin     |   horizon | target_last_day   | last_record   | extends_after_last_record   | origin_after_last_record   |   risk_units |   legacy_predicted_FH |   recorded_future_FH |   predicted_realized_ratio |
|:-----------|:-----------|----------:|:------------------|:--------------|:----------------------------|:---------------------------|-------------:|----------------------:|---------------------:|---------------------------:|
| AC-22      | 2025-12-01 |         1 | 2025-12-31        | 2026-03-31    | False                       | False                      |            2 |             0.7577778 |          119.6000000 |                  0.0063359 |
| AC-22      | 2025-12-01 |         2 | 2026-01-31        | 2026-03-31    | False                       | False                      |            2 |             1.5155556 |          257.9000000 |                  0.0058765 |
| AC-22      | 2025-12-01 |         3 | 2026-02-28        | 2026-03-31    | False                       | False                      |            2 |             2.2000000 |          362.9000000 |                  0.0060623 |

Foram inventariadas 288 combinações aeronave × origem, 37 com início da janela anterior ao primeiro registro, das quais 2 têm cobertura positiva parcial e 1 também têm unidades FH em risco, e 95 combinações aeronave × origem × horizonte com término após o último registro. Os CSV completos incluem casos sem unidades em risco e saída da aeronave; nenhum horizonte foi corrigido. Casos sem qualquer registro passado (observed_days=0), inclusive AC-18 e AC-23 antes de sua entrada, são separados das janelas parciais positivas. Unidade calendário em risco não implica necessidade de exposição FH.

## Diagnóstico de implementação e alcance

Exposure.rates divide o incremento por 90 mesmo na entrada tardia. A comparação entre exposição prevista e realizada, a contribuição localizada e a exclusão diagnóstica documentam o defeito descrito pelo autor. A16 original não estima poder válido para a regra corrigida. A5/A4 originais continuam como executadas; correções serão errata separada após o commit da emenda 006. Nenhum resultado desta análise altera parâmetros do gerador, A16 ou A9.
