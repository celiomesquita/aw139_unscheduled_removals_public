# T15 — errata de implementação da exposição prevista

Emenda 006 commitada em 6848e19. A5/A4 originais, relatórios, parâmetros do gerador e decisões pré-registradas permanecem preservados. As análises abaixo são correções de desvio de implementação, apresentadas ao lado das originais; não as substituem.

| variant   | aggregation   | criterion   | outcome_original   | outcome_corrected   | model   |   threshold |
|:----------|:--------------|:------------|:-------------------|:--------------------|:--------|------------:|
| principal | aircraft      | K2          | nula               | nula                | A5      |          30 |
| principal | aircraft      | K2          | nula               | nula                | A5      |          60 |
| principal | aircraft      | K2-A4       | mista              | favoravel           | A4      |          30 |
| principal | aircraft      | K2-idade    | nula               | favoravel           | A4      |          30 |
| principal | aircraft      | K2-A4       | mista              | favoravel           | A4      |          60 |
| principal | aircraft      | K2-idade    | nula               | favoravel           | A4      |          60 |

| model   |   threshold | criterion   |   delta_log_original |   ci_lo_original |   ci_hi_original |   delta_log_corrected |   ci_lo_corrected |   ci_hi_corrected |   w_selected_changed |   e_selected_changed |   any_probability_changed |
|:--------|------------:|:------------|---------------------:|-----------------:|-----------------:|----------------------:|------------------:|------------------:|---------------------:|---------------------:|--------------------------:|
| A5      |          30 | K2          |          -0.02827716 |      -0.12568034 |       0.03381354 |           -0.02967273 |       -0.12685707 |        0.03137850 |                   36 |                   36 |                        84 |
| A5      |          60 | K2          |          -0.02827716 |      -0.12568034 |       0.03381354 |           -0.02967273 |       -0.12685707 |        0.03137850 |                   36 |                  222 |                       270 |
| A4      |          30 | K2-A4       |          -0.00573862 |      -0.10156166 |       0.05555627 |            0.03234978 |        0.00015578 |        0.05995260 |                    6 |                    6 |                         6 |
| A4      |          30 | K2-idade    |          -0.00160820 |      -0.04053584 |       0.02480361 |            0.01372839 |        0.00078902 |        0.02779293 |                    6 |                    6 |                         6 |
| A4      |          60 | K2-A4       |          -0.00573862 |      -0.10156166 |       0.05555627 |            0.03234978 |        0.00015578 |        0.05995260 |                    6 |                    6 |                         6 |
| A4      |          60 | K2-idade    |          -0.00160820 |      -0.04053584 |       0.02480361 |            0.01372839 |        0.00078902 |        0.02779293 |                    6 |                    6 |                         6 |

Mesmas sementes e B=10 000; todas as variantes originais e limiar principal 30 dias, com sensibilidade 60 dias. realized_fh reproduziu integralmente as previsões originais em A5 e A4, nos dois limiares. exposure_errata_comparison.csv contém valores originais/corrigidos e contagens afetadas para agregado e cada P/N, inclusive sensibilidades. Mudanças em probabilidades são separadas de mudanças em marcadores; novas colunas de cobertura não são contadas como mudança preditiva.

Nenhum resultado da errata é usado para modificar A16/A9, parâmetros verdadeiros ou seleção dos 11 P/N. O manuscrito não foi editado por esta execução.
