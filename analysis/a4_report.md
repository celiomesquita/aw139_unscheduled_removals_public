# A4 — execução pós-hoc segundo A4_v1

Pré-registro preservado, revisão dd49dab42e7da50336a06efaeb2137bf55f2d19e; emenda A4_001 anterior à execução.
Famílias por mecanismo 7/2/2; log beta global; log eta por família.
Reutiliza exposição, risco concorrente, previsões, métricas e bootstrap de A5.
Escalas fixadas pelo domínio, sem seleção de escala pelos alvos de A4.

## Decisões e sensibilidades

| variant              | aggregation   | criterion   | outcome   |   predictions |   risk_spells |   aircraft |
|:---------------------|:--------------|:------------|:----------|--------------:|--------------:|-----------:|
| principal            | aircraft      | K2-A4       | mista     |         13587 |           813 |         22 |
| principal            | aircraft      | K2-idade    | nula      |         13587 |           813 |         22 |
| principal            | unit          | K2-A4       | mista     |         13587 |           813 |         22 |
| principal            | unit          | K2-idade    | nula      |         13587 |           813 |         22 |
| realized_fh          | aircraft      | K2-A4       | mista     |         13587 |           813 |         22 |
| realized_fh          | aircraft      | K2-idade    | favoravel |         13587 |           813 |         22 |
| wheels_takeoffs      | aircraft      | K2-A4       | mista     |         13587 |           813 |         22 |
| wheels_takeoffs      | aircraft      | K2-idade    | nula      |         13587 |           813 |         22 |
| imputed_takeoffs     | aircraft      | K2-A4       | mista     |         13587 |           813 |         22 |
| imputed_takeoffs     | aircraft      | K2-idade    | nula      |         13587 |           813 |         22 |
| inspection_intervals | aircraft      | K2-A4       | mista     |         13587 |           813 |         22 |
| inspection_intervals | aircraft      | K2-idade    | nula      |         13587 |           813 |         22 |
| provenance           | aircraft      | K2-A4       | favoravel |         10740 |           615 |         20 |
| provenance           | aircraft      | K2-idade    | mista     |         10740 |           615 |         20 |
| no_admin             | aircraft      | K2-A4       | mista     |         13536 |           810 |         22 |
| no_admin             | aircraft      | K2-idade    | nula      |         13536 |           810 |         22 |
| expanded_bounds      | aircraft      | K2-A4       | mista     |         13587 |           813 |         22 |
| expanded_bounds      | aircraft      | K2-idade    | nula      |         13587 |           813 |         22 |

## Principal, agregação por aeronave

| pn              |   delta_log |      ci_lo |      ci_hi |   simultaneous_lo |   simultaneous_hi |   missing_replicates | variant   | aggregation   | criterion   |
|:----------------|------------:|-----------:|-----------:|------------------:|------------------:|---------------------:|:----------|:--------------|:------------|
| aggregate       |  -0.0057386 | -0.101562  |  0.0555563 |        -0.101562  |         0.0555563 |                    0 | principal | aircraft      | K2-A4       |
| 3G3240A07531    |   0.0381994 | -0.100017  |  0.156259  |        -0.169002  |         0.203314  |                    0 | principal | aircraft      | K2-A4       |
| 3G3240V01731    |  -0.0205606 | -0.837945  |  0.508201  |        -0.837945  |         0.508201  |                  119 | principal | aircraft      | K2-A4       |
| 3G6220A01252    |   0.0490488 |  0.01055   |  0.0830746 |        -0.008223  |         0.0962926 |                    0 | principal | aircraft      | K2-A4       |
| 3G6220V02051    |   0.0814515 |  0.0450617 |  0.113164  |         0.0271911 |         0.123892  |                    0 | principal | aircraft      | K2-A4       |
| 3G6230A00833    |   0.15517   | -0.029541  |  0.347459  |        -0.111665  |         0.447933  |                    0 | principal | aircraft      | K2-A4       |
| 3G6230A00932    |   0.0428143 | -0.0277021 |  0.105819  |        -0.0673361 |         0.132238  |                    0 | principal | aircraft      | K2-A4       |
| 3G6230A00934    |   0.0236941 | -0.0540356 |  0.0861938 |        -0.103895  |         0.112273  |                    1 | principal | aircraft      | K2-A4       |
| 3G6430A00335    |   0.0523419 |  0.002529  |  0.0955926 |        -0.0263354 |         0.110835  |                    0 | principal | aircraft      | K2-A4       |
| M006-01H095-043 |   0.0156277 | -0.0337707 |  0.064135  |        -0.0566264 |         0.0843677 |                    0 | principal | aircraft      | K2-A4       |
| S-7200-514-PAX  |  -0.0679226 | -0.1325    | -0.0086641 |        -0.160483  |         0.014492  |                    0 | principal | aircraft      | K2-A4       |
| S-7200-514-PLB  |   0.0964667 | -0.0014908 |  0.192351  |        -0.0536347 |         0.236609  |                    0 | principal | aircraft      | K2-A4       |
| aggregate       |  -0.0016082 | -0.0405358 |  0.0248036 |        -0.0405358 |         0.0248036 |                    0 | principal | aircraft      | K2-idade    |
| 3G3240A07531    |  -0.026878  | -0.108787  |  0.0227243 |        -0.157829  |         0.0338691 |                    0 | principal | aircraft      | K2-idade    |
| 3G3240V01731    |  -0.193121  | -0.454557  |  0.0239904 |        -0.454557  |         0.0239904 |                  119 | principal | aircraft      | K2-idade    |
| 3G6220A01252    |   0.017252  | -0.0029377 |  0.0412471 |        -0.0098945 |         0.0547955 |                    0 | principal | aircraft      | K2-idade    |
| 3G6220V02051    |   0.0055995 | -0.0040711 |  0.0170615 |        -0.0080722 |         0.0224062 |                    0 | principal | aircraft      | K2-idade    |
| 3G6230A00833    |   0.0825533 |  0.0118867 |  0.149591  |        -0.0214824 |         0.184466  |                    0 | principal | aircraft      | K2-idade    |
| 3G6230A00932    |   0.0443581 |  0.0085831 |  0.0776976 |        -0.0096485 |         0.0941032 |                    0 | principal | aircraft      | K2-idade    |
| 3G6230A00934    |   0.0167161 | -0.0586069 |  0.0850038 |        -0.107262  |         0.119396  |                    1 | principal | aircraft      | K2-idade    |
| 3G6430A00335    |   0.0171023 | -0.0179327 |  0.0552826 |        -0.0326615 |         0.0714115 |                    0 | principal | aircraft      | K2-idade    |
| M006-01H095-043 |   0.0018686 | -0.0443246 |  0.0487627 |        -0.0650634 |         0.0697885 |                    0 | principal | aircraft      | K2-idade    |
| S-7200-514-PAX  |   0.0365638 | -0.0068105 |  0.0812266 |        -0.0219741 |         0.103741  |                    0 | principal | aircraft      | K2-idade    |
| S-7200-514-PLB  |   0.0082727 | -0.0381088 |  0.0553831 |        -0.0616193 |         0.0792001 |                    0 | principal | aircraft      | K2-idade    |

Maior log score é melhor. As duas comparações são obrigatórias; a média simples
por unidade é apenas sensibilidade. K2 nulo de A5 permanece preservado.
Nenhuma otimização A7 foi executada. T7 termina aqui, qualquer que seja o resultado.
O subconjunto elegível segundo as duas decisões está em future_policy_scope.csv;
nenhum caso é aprovado por uma sensibilidade isolada.
Hiperparâmetros, modos condicionais, falhas, fronteiras e fallbacks constam nas
tabelas de data/derived/a4/. Nenhum texto livre operacional foi exportado.
