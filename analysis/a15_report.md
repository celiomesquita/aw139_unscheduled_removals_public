# A15 — robustez descritiva temporal

Desenho posterior ao conhecimento de A4. Previsões congeladas, sem novo ajuste. Origens jan–jun e jul–dez/2025; os alvos de horizontes sobrepostos não são amostras independentes. Nenhuma regra de decisão é aplicada aos semestres.

Mesmo código de métricas e bootstrap de A5/A4: 24 códigos de aeronave, 10 000 reamostragens, PCG64 20261112, agregação por aeronave e Bonferroni para 11 P/N. IC 95% descritivos; não corrigidos entre semestres/variantes.

| variant     | period   | criterion   |   delta_log |     ci_lo |    ci_hi |   predictions |   aircraft |
|:------------|:---------|:------------|------------:|----------:|---------:|--------------:|-----------:|
| principal   | 2025     | K2-A4       |   -0.005739 | -0.101562 | 0.055556 |         13587 |         22 |
| principal   | 2025     | K2-idade    |   -0.001608 | -0.040536 | 0.024804 |         13587 |         22 |
| principal   | jan-jun  | K2-A4       |    0.037760 |  0.001878 | 0.067570 |          6717 |         21 |
| principal   | jan-jun  | K2-idade    |    0.017788 |  0.002701 | 0.033111 |          6717 |         21 |
| principal   | jul-dez  | K2-A4       |   -0.009433 | -0.108207 | 0.059342 |          6870 |         22 |
| principal   | jul-dez  | K2-idade    |   -0.004860 | -0.045059 | 0.024883 |          6870 |         22 |
| realized_fh | 2025     | K2-A4       |    0.012171 | -0.060595 | 0.067689 |         13587 |         22 |
| realized_fh | 2025     | K2-idade    |    0.016413 |  0.002763 | 0.030499 |         13587 |         22 |
| realized_fh | jan-jun  | K2-A4       |    0.053703 |  0.016546 | 0.084584 |          6717 |         21 |
| realized_fh | jan-jun  | K2-idade    |    0.022645 |  0.007263 | 0.038145 |          6717 |         21 |
| realized_fh | jul-dez  | K2-A4       |   -0.027817 | -0.154970 | 0.064667 |          6870 |         22 |
| realized_fh | jul-dez  | K2-idade    |    0.010650 | -0.008285 | 0.028875 |          6870 |         22 |

As 12 origens reproduzem exatamente todos os intervalos publicados de A4 (igualdade dos valores float64 com leitura round_trip), além de log score, Brier, contagens e fallback de todos os modelos publicados. Detalhes por P/N em `data/derived/a15/intervals.csv`; métricas e calibração nos CSV adjacentes.

Na variante principal, o ganho médio da idade é positivo em jan–jun e negativo em jul–dez. Com FH realizadas, os dois valores pontuais são positivos, com maior incerteza no segundo semestre. Isso descreve variação temporal; não é um teste independente de mudança nem altera K2-idade. O agregado anual não é a média simples dos semestres: a composição de aeronaves e origens observáveis difere.

## Verificação B = 999 para o futuro A16

| variant     | criterion   | B10000    | B999      | same_decision   | passed10000               | passed999                 | same_PN   |
|:------------|:------------|:----------|:----------|:----------------|:--------------------------|:--------------------------|:----------|
| principal   | K2-A4       | mista     | mista     | True            | 3G6220V02051              | 3G6220V02051              | True      |
| principal   | K2-idade    | nula      | nula      | True            |                           |                           | True      |
| realized_fh | K2-A4       | mista     | mista     | True            | 3G6220V02051              | 3G6220V02051              | True      |
| realized_fh | K2-idade    | favoravel | favoravel | True            | 3G6230A00833;3G6230A00932 | 3G6230A00833;3G6230A00932 | True      |

Esta comparação verifica decisões reais; não estabelece equivalência de caudas Monte Carlo em todas as futuras amostras sintéticas. FH realizadas permanece hipótese gerada pelos dados, sem confirmação independente.
