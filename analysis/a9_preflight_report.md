# A9/A10 — conferência anterior ao piloto

14/11/2026. O autor autorizou o início após a conclusão de T16.

Estado: **blocked_missing_mh**. Nenhuma réplica de piloto ou de política gerada.

A16 corrigida concluiu 1 800 réplicas e aprovou os controles. Os hashes
históricos foram conferidos e permanecem intactos. O pré-registro e a
emenda 006 correspondem às versões commitadas.

## MH preventiva exigida pelo protocolo

Fonte: T4, soma de linhas por documento com uma única remoção, mediana por P/N.
As faixas empíricas Q1/Q3 são preservadas. Nenhum coeficiente foi imputado.

| P/N | Documentos | Com MH | MH central |
|---|---|---|---|
| 3G3240A07531 | 141 | 141 | 5.0 |
| 3G3240V01731 | 44 | 44 | 5.0 |
| 3G6220A01252 | 2 | 2 | 24.0 |
| 3G6220V02051 | 9 | 6 | 6.5 |
| 3G6230A00833 | 0 | 0 | indisponível |
| 3G6230A00932 | 0 | 0 | indisponível |
| 3G6230A00934 | 1 | 1 | 9.0 |
| 3G6430A00335 | 0 | 0 | indisponível |
| M006-01H095-043 | 24 | 22 | 9.0 |
| S-7200-514-PAX | 29 | 29 | 2.0 |
| S-7200-514-PLB | 29 | 29 | 3.0 |

O pré-registro A16/A9, seção 6, determina: “Falta de MH não vira zero:
parar a instanciação desse P/N e informar o autor.” Os três P/N sem
coeficiente não têm documentos de remoção única nesta base. Há estimativas
por rateio em documentos compartilhados, mas pertencem à sensibilidade
e não substituem a fonte principal sem emenda explícita do autor.

A capacidade de cada visita depende da soma das MH das unidades ativas;
assim, a lacuna impede instanciar a comparação completa pré-especificada.
Não foram excluídos P/N, reduzida a grade ou medidas durações de um piloto
parcial. R de A9 ainda não foi calculado e o orçamento continua em 120 h.

## Dependência computacional

python-mip importável no interpretador py -3: **False**.
A instalação do solver e seus testes de ótimo/renovação precederão o piloto.
A conferência de insumos não certifica prontidão do simulador/MILP.

## Desbloqueio

O autor precisa definir a fonte de MH para os três P/N ou autorizar, por
emenda, uma aproximação explícita com suas limitações e sensibilidades.
Manter os 11 P/N e a grade; não escolher valores pelo ganho de política.
