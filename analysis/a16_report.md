# T12 / A16 — validação do gerador e piloto

Pré-registro A16_A9_v1, commit aa129e2, com alterações do autor anteriores à simulação: η ajustado para preservar vida média ao variar β; visitas reais; 168 h de máquina (48 h A16, 120 h A9/A10). Arquivo preservado.

## Gerador estacionário: barreira aprovada

1289 marcos reais, 609 canais sintéticos, 24 aeronaves. A coloração preserva datas e observação, sem alegar identificação de posições físicas. Quatro eventos reais de idade zero foram excluídos das taxas como em A4, mantendo seus marcos. FH, decolagens e máscaras diárias foram preservadas; a exposição reconstruída confere com a soma dos trechos.

1 000 réplicas por nível (calibrado, β=1, ampliado), 3 000 no total, sem reajuste dos parâmetros reais. Intervalo preditivo central por P/N com α=0,05/11; o nível calibrado governa a decisão. Taxas por FH ou dia conforme a escala fixada. mc_se mede a incerteza da média simulada, não a dispersão preditiva nem incerteza do parâmetro estimado.

| pn              |   real_rate |   simulated_rate |   predictive_lo |   predictive_hi |   simulated_real_ratio |      mc_se | within_interval   |
|:----------------|------------:|-----------------:|----------------:|----------------:|-----------------------:|-----------:|:------------------|
| 3G3240A07531    |  0.00289838 |       0.00304802 |      0.00251827 |      0.00356222 |             1.05162821 | 0.00000578 | True              |
| 3G3240V01731    |  0.00396816 |       0.00393054 |      0.00293644 |      0.00507924 |             0.99052000 | 0.00001225 | True              |
| 3G6220A01252    |  0.00046310 |       0.00047136 |      0.00027265 |      0.00068459 |             1.01782609 | 0.00000226 | True              |
| 3G6220V02051    |  0.00025973 |       0.00029112 |      0.00015037 |      0.00043374 |             1.12084211 | 0.00000153 | True              |
| 3G6230A00833    |  0.00309267 |       0.00306983 |      0.00272883 |      0.00345652 |             0.99261176 | 0.00000452 | True              |
| 3G6230A00932    |  0.00109065 |       0.00108388 |      0.00063143 |      0.00154987 |             0.99378947 | 0.00000563 | True              |
| 3G6230A00934    |  0.00066527 |       0.00072863 |      0.00034763 |      0.00109378 |             1.09525000 | 0.00000424 | True              |
| 3G6430A00335    |  0.00029163 |       0.00030907 |      0.00014582 |      0.00049430 |             1.05978571 | 0.00000198 | True              |
| M006-01H095-043 |  0.00060794 |       0.00057522 |      0.00034739 |      0.00079747 |             0.94617857 | 0.00000265 | True              |
| S-7200-514-PAX  |  0.00194560 |       0.00157171 |      0.00116482 |      0.00205820 |             0.80782828 | 0.00000516 | True              |
| S-7200-514-PLB  |  0.00439217 |       0.00423750 |      0.00321526 |      0.00519344 |             0.96478289 | 0.00001053 | True              |

Os 11 P/N passaram pelo critério pré-especificado. As razões simulada/real diferem de 1, principalmente para o colete PAX; aprovação por intervalo preditivo não é equivalência das taxas nem validação de toda a distribuição. Os níveis β=1 e ampliado permanecem descritivos em rate_validation.csv.

## Idades na remoção

| pn              |   real_q10 |   real_q50 |   real_q90 |   simulated_q10 |   simulated_q50 |   simulated_q90 |   normalized_wasserstein |
|:----------------|-----------:|-----------:|-----------:|----------------:|----------------:|----------------:|-------------------------:|
| 3G3240A07531    |    69.8500 |   220.2500 |   352.7000 |         53.3916 |        203.2928 |        479.0475 |                   0.1854 |
| 3G3240V01731    |    94.8300 |   161.9500 |   368.3200 |         55.5951 |        189.0341 |        412.9312 |                   0.2728 |
| 3G6220A01252    |   263.6800 |   723.1000 |  1284.4200 |        287.6795 |        763.8093 |       1401.4536 |                   0.1118 |
| 3G6220V02051    |   511.2200 |   948.5000 |  1961.2400 |        388.9090 |       1023.9794 |       1746.4943 |                   0.1004 |
| 3G6230A00833    |   206.4800 |   271.8000 |   369.7000 |        141.5344 |        275.3444 |        422.7653 |                   0.1178 |
| 3G6230A00932    |   223.2800 |   635.1000 |  1031.4200 |        179.2362 |        529.9630 |       1038.5229 |                   0.1619 |
| 3G6230A00934    |   458.9600 |   690.4500 |  1594.3800 |        294.0343 |        747.5474 |       1405.1194 |                   0.2726 |
| 3G6430A00335    |   802.5000 |  1012.2000 |  1635.0100 |        459.4237 |        997.8019 |       1505.6242 |                   0.1311 |
| M006-01H095-043 |   493.4800 |   783.7500 |  1416.5600 |        261.4733 |        725.7511 |       1386.0480 |                   0.1078 |
| S-7200-514-PAX  |    25.0000 |   141.0000 |   224.0000 |         34.4350 |        127.7323 |        304.7387 |                   0.1674 |
| S-7200-514-PLB  |    25.1000 |    98.5000 |   216.6000 |         16.5627 |         80.1880 |        221.4356 |                   0.1702 |

Quantis de 10/50/90% e distância de Wasserstein dividida pela mediana real. Discrepâncias foram preservadas, sem recalibração. A ECDF real pode ser reconstruída de real_event_ages.csv; as idades simuladas completas estão em latent_spells.csv.gz (filtrar observed=1, risk=1, age>0). A grade de 201 quantis é uma representação adicional das distribuições.

## Reprodução e testes

Duas execuções completas geraram 12 artefatos idênticos por SHA256; 100 testes aprovados. O único teste excluído reexecutaria A5, vedado nesta rodada. A5, A4, seus pré-registros, o novo pré-registro e o manuscrito ficaram intactos. verification.json documenta o estado anterior ao piloto. As emendas 001 (antes da geração) e 002 (antes do piloto) explicitam as convenções de observação e de adaptação, sem alterar pré-registros.

## Piloto de tempo, excluído dos resultados

|   replicate |   seconds |   process_peak_bytes |   synthetic_spells |   incomplete_fragments_excluded |
|------------:|----------:|---------------------:|-------------------:|--------------------------------:|
|       0.000 |    76.688 |        364343296.000 |           6176.000 |                         568.000 |
|       1.000 |    46.974 |        365305856.000 |           6226.000 |                         568.000 |
|       2.000 |    44.977 |        366329856.000 |           6108.000 |                         568.000 |
|       3.000 |    47.165 |        366960640.000 |           6264.000 |                         568.000 |
|       4.000 |    42.000 |        367427584.000 |           6199.000 |                         568.000 |

Maior tempo: 76.688 s por réplica ×4 (duas variantes, B=999). Para R≥200 nas nove células, a regra exige tempo ≤64 s por réplica; reserva de 1,5 incluída. R pela fórmula: 150; estimativa conservadora para R=200: 57.516 h frente às 48 h reservadas. Métricas/rejeições do piloto não foram inspecionadas ou incorporadas a resultados de poder.

**Parada obrigatória de orçamento:** R≥200 não cabe. Não reduzir grade ou R nem transferir as 120 h de A9/A10. Nenhum resultado de poder, erro tipo I ou economia foi produzido; A9/A10 não iniciadas. O autor deve decidir a revisão de orçamento por emenda antes de prosseguir.
