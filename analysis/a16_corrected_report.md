# T16 — A16 corrigida, fluxo 17

Emenda 006 commitada em 6848e19. R=200, B=999, seis processos; orçamento A16 de 60 h com custos anteriores acumulados. Controles antigos estão invalidados pelo defeito para esta finalidade e não entram nas estimativas novas.

Estado: **complete**. Réplicas novas concluídas: 1800 de 1 800.

## Controles antigos, preservados

| cell    | variant     | estimand   |   frequency |   failures |
|:--------|:------------|:-----------|------------:|-----------:|
| null_x1 | principal   | aggregate  |     0.00000 |          0 |
| null_x1 | principal   | family     |     0.07500 |          0 |
| null_x1 | realized_fh | aggregate  |     0.00000 |          0 |
| null_x1 | realized_fh | family     |     0.03500 |          0 |
| null_x2 | principal   | aggregate  |     0.00000 |          0 |
| null_x2 | principal   | family     |     0.03500 |          0 |
| null_x2 | realized_fh | aggregate  |     0.00000 |          0 |
| null_x2 | realized_fh | family     |     0.02500 |          0 |
| null_x4 | principal   | aggregate  |     0.15000 |          0 |
| null_x4 | principal   | family     |     0.02000 |          0 |
| null_x4 | realized_fh | aggregate  |     0.00000 |          1 |
| null_x4 | realized_fh | family     |     0.01500 |          1 |

## Resultados corrigidos

| cell          | variant     | estimand   |   frequency |   ci_lo |   ci_hi |   failures |
|:--------------|:------------|:-----------|------------:|--------:|--------:|-----------:|
| null_x1       | principal   | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x1       | principal   | family     |     0.04500 | 0.02385 | 0.08330 |          0 |
| null_x1       | realized_fh | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x1       | realized_fh | family     |     0.04000 | 0.02041 | 0.07693 |          0 |
| null_x2       | principal   | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x2       | principal   | family     |     0.03500 | 0.01706 | 0.07047 |          0 |
| null_x2       | realized_fh | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x2       | realized_fh | family     |     0.02500 | 0.01072 | 0.05718 |          0 |
| null_x4       | principal   | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x4       | principal   | family     |     0.03000 | 0.01382 | 0.06389 |          0 |
| null_x4       | realized_fh | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x4       | realized_fh | family     |     0.01500 | 0.00511 | 0.04317 |          0 |
| calibrated_x1 | principal   | aggregate  |     0.99500 | 0.97223 | 0.99912 |          0 |
| calibrated_x1 | principal   | family     |     0.89000 | 0.83907 | 0.92623 |          0 |
| calibrated_x1 | realized_fh | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x1 | realized_fh | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x2 | principal   | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x2 | principal   | family     |     0.99500 | 0.97223 | 0.99912 |          0 |
| calibrated_x2 | realized_fh | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x2 | realized_fh | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x4 | principal   | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x4 | principal   | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x4 | realized_fh | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| calibrated_x4 | realized_fh | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x1  | principal   | aggregate  |     0.99500 | 0.97223 | 0.99912 |          0 |
| amplified_x1  | principal   | family     |     0.98000 | 0.94971 | 0.99220 |          0 |
| amplified_x1  | realized_fh | aggregate  |     0.99000 | 0.96428 | 0.99725 |          0 |
| amplified_x1  | realized_fh | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x2  | principal   | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x2  | principal   | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x2  | realized_fh | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x2  | realized_fh | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x4  | principal   | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x4  | principal   | family     |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x4  | realized_fh | aggregate  |     1.00000 | 0.98115 | 1.00000 |          0 |
| amplified_x4  | realized_fh | family     |     1.00000 | 0.98115 | 1.00000 |          0 |

Wilson 95% e erro Monte Carlo, falhas no denominador e limites alternativos em summary.csv. Limiar 60 dias é funcionalmente equivalente a 30 em todas as origens externas destes relógios; isso não vale automaticamente para A5 ou A9.

A16 concluída. Para modos A4, poder ≥0,8 sugere pequeno valor preditivo da idade sob o gerador; <0,5 é inconclusivo; 0,5–0,8 é evidência fraca. Considerar intervalos e tamanho; FH realizadas continua hipótese gerada pelos dados. Próxima etapa: piloto A9/A10.
