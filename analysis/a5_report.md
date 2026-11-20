# A5 — validação preditiva temporal e decisão K2

Pré-registro A5_v1 preservado, revisão aed4c3a618bd049fcf0e366f737645d878baddaa; emenda A5_001 anterior
à execução. Coorte principal dos 11 candidatos K1, com seleção
temporal interna, riscos concorrentes, bootstrap de aeronaves e seis variantes.

## Decisão principal e sensibilidades

| variant              | outcome   |   unit_predictions |   risk_spells |   aircraft |
|:---------------------|:----------|-------------------:|--------------:|-----------:|
| principal            | nula      |              13587 |           813 |         22 |
| realized_fh          | nula      |              13587 |           813 |         22 |
| imputed_takeoffs     | nula      |              13587 |           813 |         22 |
| inspection_intervals | nula      |              13587 |           813 |         22 |
| provenance           | mista     |              10740 |           615 |         20 |
| no_admin             | nula      |              13536 |           810 |         22 |

## Diferenças pareadas do log score, principal

| pn              |   delta_log |      ci_lo |      ci_hi |   simultaneous_lo |   simultaneous_hi |   missing_replicates | variant   |
|:----------------|------------:|-----------:|-----------:|------------------:|------------------:|---------------------:|:----------|
| aggregate       |  -0.0282772 | -0.12568   |  0.0338135 |        -0.12568   |         0.0338135 |                    0 | principal |
| 3G3240A07531    |  -0.0497562 | -0.239297  |  0.125459  |        -0.330077  |         0.19524   |                    0 | principal |
| 3G3240V01731    |   0.331357  | -0.05618   |  0.620085  |        -0.05618   |         0.620085  |                  119 | principal |
| 3G6220A01252    |   0.0500134 |  0.0104508 |  0.0849337 |        -0.0097968 |         0.0982368 |                    0 | principal |
| 3G6220V02051    |   0.0262745 |  0.0012115 |  0.0496391 |        -0.01145   |         0.059885  |                    0 | principal |
| 3G6230A00833    |   0.0089159 |  0         |  0.0280279 |         0         |         0.0419519 |                    0 | principal |
| 3G6230A00932    |   0.0110253 | -0.0047425 |  0.0344727 |        -0.0090513 |         0.051587  |                    0 | principal |
| 3G6230A00934    |  -0.0192369 | -0.0824149 |  0.0387936 |        -0.118325  |         0.0702725 |                    1 | principal |
| 3G6430A00335    |   0.0223833 |  0.0055833 |  0.037027  |        -0.0034511 |         0.042853  |                    0 | principal |
| M006-01H095-043 |  -0.0268113 | -0.0806792 |  0.0185506 |        -0.104981  |         0.0341707 |                    0 | principal |
| S-7200-514-PAX  |  -0.044083  | -0.0871494 | -0.0076514 |        -0.109509  |         0.0044391 |                    0 | principal |
| S-7200-514-PLB  |   0.106468  | -0.0357662 |  0.255377  |        -0.101675  |         0.31996   |                    0 | principal |

Maior é melhor. IC agregado 95%; por P/N também intervalos simultâneos Bonferroni.
K2 usa somente o principal; sensibilidades não substituem seu critério. K1 foi
selecionado na janela completa: K2 é condicionado a essa seleção retrospectiva.
Não constitui validação externa nem demonstra ganho económico do ciclo dinâmico.
Comparação Weibull–exponencial, Brier, calibração, cobertura e fallbacks disponíveis
nas tabelas de métricas; menor Brier é melhor. A interpretação física da vida e
a transportabilidade para políticas alternativas permanecem limitações.

Artefatos em `data/derived/a5/`: predições individuais, contagens, cobertura,
casos completos, ajustes, seleção de escala, métricas, calibração, bootstrap,
sensibilidades e manifesto de versões/hashes. Nenhum texto livre foi exportado.
