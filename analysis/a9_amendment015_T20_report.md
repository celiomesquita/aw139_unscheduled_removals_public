# Emenda 015 — T20 interrompida pela salvaguarda de 3 h

A verificação da calibração passou nos nove contextos. A T20 foi interrompida pela salvaguarda de 3 h e não produziu uma réplica pareada completa. Todos os PIDs registrados do executor estão encerrados. Nenhum ensaio técnico ou execução principal foi iniciado; nenhum commit foi realizado.

O erro registrado foi `T20_THREE_HOUR_WATCHDOG_OR_GLOBAL_DEADLINE`, após 10800.022844808 s. Os aproximadamente 22.845 ms além de 10.800 s incluem os registros e o encerramento após o timeout; o timer permaneceu fixado em 10.800 s. O último registro de recursos é de 2026-11-20T14:48:28.788799+00:00.

## Calibração aprovada

N=9, mesmo avaliador e grade de ¼ de dia, parâmetros, pesos e amostra congelados. Maior g = 0.0010851932165972967 (0.10851932%), contra o limite 0,5%; todos os ramos coincidiram. Q(a_barato), Q(a_exato), g, idades, deslocamentos e diagnósticos estão em `data/derived/a9/amendment015/verification_table.csv`, `verification/00.json` a `08.json` e `verification_manifest.json`. O relatório próprio é `analysis/a9_amendment015_verification_report.md`.

## Completude da T20 e tempos preservados

Célula 71, réplica dedicada 5, fora de R e do ensaio técnico 0..4, com seis políticas previstas. Não houve redução de grade, políticas, R, resolução ou precisão.

| Política | Estado | Meses completos | Parede da política (s) |
|---|---|---:|---:|
| P0 | completa | 24 | 6.777343 |
| P1 | completa | 24 | 107.595489 |
| P2 | completa | 24 | 4270.514310 |
| P3 | completa | 24 | 4428.789289 |
| P2_fixed | parcial | 15 | 1980.987249 |
| P2_age | não iniciada | 0 | não medida |

Foram encerrados 111 meses completos. Há mais um registro parcial de P2_fixed, mês 16 (índice 15, origem 2025-04-01). O tratador do timeout fecha esse mês e grava a etapa `complete_policy` ativa no bloco finally; esses registros são parciais, não certificados de conclusão. `profile/partial_timing_annotations.json` explicita essa classificação.

A interrupção ocorreu na construção/avaliação dos custos dos arcos do planejamento, durante a integração do ciclo terminal (`a9_terminal.py`), conforme traceback preservado.

| Etapa | Registros | Soma diagnóstica de parede (s) |
|---|---:|---:|
| A4_fit | 23 | 59.328172 |
| MILP | 1176 | 230.517139 |
| age_calibration | 1 | 1.650943 |
| auxiliary_generation_and_writing | 1 | 0.138629 |
| complete_policy | 5 | 10794.663680 |
| historical_calendars | 1 | 0.255073 |
| initial_A4_fit | 1 | 1.715844 |
| loading | 1 | 0.576833 |
| planning | 64 | 10603.393919 |

As somas de etapas são aninhadas: MILP pertence ao planejamento, e as etapas mensais pertencem à política. Não são somadas para reconstruir o ledger. Os últimos registros de planejamento/política/mês são parciais. Tempos por etapa e mês, CPU, RSS e contagens estão em `profile/stages.jsonl`, `months.json`, `resources.jsonl`, `stage_timing_summary.csv` e `failure.json`.

Pico observado: 8 processos Python, RSS agregado 1754927104 bytes (1.634403 GiB), dentro da alocação de 17662817894 bytes. CPU user+system amostrada por PIDs distintos: 11072.300000 s, limite inferior amostral; lacunas de processos curtos não foram imputadas. CPU não foi somada à parede nem dividida pelo número de trabalhadores.

## Ledger e critério de escopo

Atualização: 2026-11-20T14:50:53.730782+00:00. Início global: 2026-11-18T15:57:28+00:00; prazo global: 2026-12-02T15:57:28+00:00. **C = 168805.730782 s = 46.890480773 h; saldo = 1040794.269218 s = 289.109519227 h.** C é apenas o tempo corrido desde o commit 2d7e19d, incluindo pausas, referências, verificação e T20. As durações acima já pertencem a C e não são acrescentadas novamente.

**t71 completo, T_base_restante e T_restante_projetado não estão disponíveis.** O resultado formal do critério de escopo da seção 7 fica não avaliado por impedimento técnico: a T20 não terminou. A própria seção determina que, nesse caso, se preserve o estado e se informe o impedimento, sem inventar duração completa ou previsão pontual. Não se extrapolou o tempo parcial para completar as políticas pendentes. O plano prospectivo de projeção em `profile/remaining_projection_plan.json` permanece preservado, sem aplicação a um t71 inexistente.

Continuam pendentes 14.400 réplicas principais (72 × 200) e cinco réplicas de ensaio técnico; a réplica de perfilamento permanece fora de R. Nenhuma célula, política ou réplica foi retirada, nem o ensaio técnico foi declarado concluído. Não há nova decisão de escopo ou autorização de execução neste relatório.

## Integridade e parada

O manifesto e os nove certificados exatos foram reconferidos. Os oito certificados anteriores mantêm bytes e mtime. Fontes numéricas, configuração e módulos prospectivos congelados permanecem iguais; o adendo conserva o prefixo commitado. A entrada nova reconhece apenas a exceção das referências já auditada e o relógio da T20, sem mudar cálculos históricos. Os hashes de encerramento estão em `profile/closure_integrity.json`.

Ganhos e alarmes continuam fechados. Logs, traceback, estado parcial e tempos estão preservados. Parada por impedimento técnico, sem ensaio técnico, execução principal ou commit.
