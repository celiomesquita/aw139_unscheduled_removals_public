# A16 — execução principal

Pré-registro aa129e2, emenda de orçamento 003 commitada em 9c1a0ee. A16: 60 h; A9/A10: 120 h; R=200 por célula, B=999, nove células e duas variantes. O piloto de cinco réplicas continua excluído.

Estado: **stopped_type_I**. Réplicas principais concluídas: 600 de 1 800. Células nulas ×1, ×2 e ×4 precedem as células de efeito. Frequências parciais não acionam a parada.

| cell    | variant     | estimand   |   frequency |   ci_lo |   ci_hi |   failures |
|:--------|:------------|:-----------|------------:|--------:|--------:|-----------:|
| null_x1 | principal   | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x1 | principal   | family     |     0.07500 | 0.04597 | 0.12004 |          0 |
| null_x1 | realized_fh | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x1 | realized_fh | family     |     0.03500 | 0.01706 | 0.07047 |          0 |
| null_x2 | principal   | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x2 | principal   | family     |     0.03500 | 0.01706 | 0.07047 |          0 |
| null_x2 | realized_fh | aggregate  |     0.00000 | 0.00000 | 0.01885 |          0 |
| null_x2 | realized_fh | family     |     0.02500 | 0.01072 | 0.05718 |          0 |
| null_x4 | principal   | aggregate  |     0.15000 | 0.10714 | 0.20606 |          0 |
| null_x4 | principal   | family     |     0.02000 | 0.00780 | 0.05029 |          0 |
| null_x4 | realized_fh | aggregate  |     0.00000 | 0.00000 | 0.01885 |          1 |
| null_x4 | realized_fh | family     |     0.01500 | 0.00511 | 0.04317 |          1 |

Wilson 95%, unidade: réplica. Falhas permanecem no denominador como não detecção; limites alternativos e resultados por P/N constam de summary.csv. Todas as linhas acima correspondem a células completas, com 200 réplicas.

**Parada pré-registrada:** erro tipo I agregado/familiar acima de 0,10 ou controle não avaliável. Não interpretar poder ou iniciar A9/A10.

Execução multicore: 6 processos, um thread numérico por processo. Configuração científica original preservada; reproduções paralelas não contam como réplicas adicionais.

Alteração editorial externa no manuscrito registrada separadamente; os artefatos científicos A4/A5 e pré-registros permanecem protegidos.
