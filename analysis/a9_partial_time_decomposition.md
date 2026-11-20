# Decomposição computacional da réplica parcial A9

15/11/2026. Entrega anterior à preparação da emenda 014. Nenhum desfecho aberto.

PID 34396 e seis filhos encerrados por autorização expressa às 2026-11-15T23:07:54.890998+00:00.
Estado, logs e checkpoint parcial preservados; réplica 0 excluída de R, sem conclusão forçada.

Tempo de parede medido: **86954.802319 s (24.154112 h)**. CPU amostrada acumulada: **≥149911.968750 s**; CPU paralela não é somada ao orçamento de parede.
Pico agregado de RSS amostrado: **28375977984 bytes (26.427 GiB)**; não atribuível a uma etapa.
RSS agregado no instante da interrupção, em junho/P2_age: **11025883136 bytes (10.269 GiB)**. É uma observação pontual, não o pico da etapa.

## Limites de recuperação

stdout.log contém eventos sem relógio; state.json foi sobrescrito. O monitor conservava somente máximos globais. Tempos dos jobs, contagens de breakpoints e diagnósticos completos ficaram em RAM até o final das seis políticas e não foram persistidos antes da interrupção. Não existe perfil por etapa recuperável. NA significa não registrado; nunca significa zero.

Cada chamada de calibração emite pulsos separados por pelo menos 5 s (a9_parallel.py). N pulsos certificam ≥5(N−1) s, não uma duração exata. O limite superior de cada etapa alcançada é o total menos os limites inferiores das outras etapas. Os limites superiores não são aditivos. Os limites dos meses incluem ajuste e simulação, enquanto seus limites inferiores provêm apenas da calibração. Não se estima tempo multiplicando pulsos por uma cadência suposta exata.

Calibrações consumiram **≥74830 s (20.7861 h)**. O restante não atribuível é **≤12124.802319 s**; inclui atrasos dos pulsos e todas as outras operações.

## Etapas solicitadas

| Etapa | Estado | Parede: limite inferior–superior (s) | Pico RSS medido por etapa | Máxima reserva estimada (GiB) |
|---|---|---:|---|---:|
| Aquecimento + ajuste inicial | concluído | 0–12124.802 | NA | NA |
| Calibração inicial P1 | concluída | 13720–25844.802 | NA | 24.598 |
| P0 — 24 meses | concluída | 0–12124.802 | NA | NA |
| P1 — 24 meses | concluída | 0–12124.802 | NA | NA |
| P2 — 24 meses | concluída | 0–12124.802 | NA | NA |
| P3 — 24 meses | concluída | 0–12124.802 | NA | NA |
| P2_noreest (P2_fixed) — 24 meses | concluída | 0–12124.802 | NA | NA |
| P2_age 2024-01 | concluído | 0–12124.802 | NA | NA |
| P2_age 2024-02 | concluído | 15575–27699.802 | NA | 23.371 |
| P2_age 2024-03 | concluído | 14925–27049.802 | NA | 24.598 |
| P2_age 2024-04 | concluído | 15205–27329.802 | NA | 24.676 |
| P2_age 2024-05 | concluído | 15110–27234.802 | NA | 22.704 |
| P2_age 2024-06 | interrompido | 295–12419.802 | NA | 10.422 |
| P2_age 2024-07 | não iniciado | NA | NA | NA |
| P2_age 2024-08 | não iniciado | NA | NA | NA |
| P2_age 2024-09 | não iniciado | NA | NA | NA |
| P2_age 2024-10 | não iniciado | NA | NA | NA |
| P2_age 2024-11 | não iniciado | NA | NA | NA |
| P2_age 2024-12 | não iniciado | NA | NA | NA |
| P2_age 2025-01 | não iniciado | NA | NA | NA |
| P2_age 2025-02 | não iniciado | NA | NA | NA |
| P2_age 2025-03 | não iniciado | NA | NA | NA |
| P2_age 2025-04 | não iniciado | NA | NA | NA |
| P2_age 2025-05 | não iniciado | NA | NA | NA |
| P2_age 2025-06 | não iniciado | NA | NA | NA |
| P2_age 2025-07 | não iniciado | NA | NA | NA |
| P2_age 2025-08 | não iniciado | NA | NA | NA |
| P2_age 2025-09 | não iniciado | NA | NA | NA |
| P2_age 2025-10 | não iniciado | NA | NA | NA |
| P2_age 2025-11 | não iniciado | NA | NA | NA |
| P2_age 2025-12 | não iniciado | NA | NA | NA |

Reserva é previsão de matrizes dos jobs pendentes, não RSS observado nem máximo real. Aquecimento reutilizou a coorte persistida; sua geração anterior não foi repetida. A duração exata de carga/ajuste não foi registrada. P2_noreest corresponde a P2_fixed no código.

## Limiares e fases por P/N

Contagens efetivamente avaliadas: **NA para todos os P/N, em todas as chamadas**. As colunas seguintes reconstroem somente o tamanho declarado das matrizes de fases (soma dos calendários informativos), usando exclusivamente a coorte auxiliar já congelada. Não são contagens de fases realmente visitadas, nem de limiares. Cada calendário tem 365/730/1460 fases nas grades 1/2/4; a grade 4 é condicional ao refinamento. β≤1 usa o ramo sem prevenção, sem enumeração de limiares. Não se pode inferir a grade atingida nem a quantidade de breakpoints de uma lista de P/N pendentes.

| P/N | Contextos informativos/total | Fases declaradas grade 1 | grade 2 | grade 4 | Limiares reais | Fases reais |
|---|---:|---:|---:|---:|---|---|
| 3G3240A07531 | 18/19 | 6570 | 13140 | 26280 | NA | NA |
| 3G3240V01731 | 3/3 | 1095 | 2190 | 4380 | NA | NA |
| 3G6220A01252 | 13/13 | 4745 | 9490 | 18980 | NA | NA |
| 3G6220V02051 | 17/17 | 6205 | 12410 | 24820 | NA | NA |
| 3G6230A00833 | 12/12 | 4380 | 8760 | 17520 | NA | NA |
| 3G6230A00932 | 7/7 | 2555 | 5110 | 10220 | NA | NA |
| 3G6230A00934 | 3/3 | 1095 | 2190 | 4380 | NA | NA |
| 3G6430A00335 | 12/12 | 4380 | 8760 | 17520 | NA | NA |
| M006-01H095-043 | 15/15 | 5475 | 10950 | 21900 | NA | NA |
| S-7200-514-PAX | 13/13 | 4745 | 9490 | 18980 | NA | NA |
| S-7200-514-PLB | 16/16 | 5840 | 11680 | 23360 | NA | NA |

## Ledger e disponibilidade

Anterior congelado: 2825.432359 s. Acrescentado uma única vez: 86954.802319 s. Acumulado conhecido: **89780.234678 s (24.938954 h)**. Restante: **≤95.061046 h**. Lacunas anteriores continuam explícitas; não há reinício do orçamento.

Arquivos: data/derived/a9/decomposition/{decomposition.json,stages.csv,pn_counts.csv,accumulated_costs.json}. decomposition.json contém hashes dos registros e do reconstrutor. O ledger anterior foi preservado sem alteração.
