# Emenda 015 — parada técnica na admissão das referências

Registro de 18/11/2026, posterior ao commit autorizado `2d7e19d`.
**Estado: STOP por memória; T20 não iniciada. Nenhum commit realizado.**

## Resultado e impedimento

O estimador histórico `a9_parallel.estimated_grid_bytes`, aplicado sem redução
à grade de ¼ de dia e a todas as aeronaves/pesos de cada contexto composto,
estima **39.370.577.920 bytes (36,6667 GiB)** para o contexto 06,
P/N 3G6430A00335, r=10. A alocação congelada é
**17,662,817,894 bytes (16.4498 GiB)**,
70% dos 25,232,596,992 bytes disponíveis no início.
É uma estimativa conservadora do avaliador histórico, não RSS medido de uma busca.
Mesmo isolado, esse contexto excede a alocação. A admissão recusou o bloco antes
de criar trabalhadores ou calcular referências; serializar contextos não elimina
esse excesso individual. Nenhuma precisão, grade, parâmetro, peso ou amostra mudou.

| Contexto | P/N | r | Memória estimada (GiB) | Cabe na alocação? |
|---|---|---:|---:|---|
| 00 | 3G6230A00833 | 2 | 3.8502 | sim |
| 01 | 3G3240V01731 | 2 | 2.9842 | sim |
| 02 | S-7200-514-PAX | 2 | 1.3120 | sim |
| 03 | 3G6230A00833 | 5 | 3.8502 | sim |
| 04 | 3G3240A07531 | 5 | 10.9793 | sim |
| 05 | S-7200-514-PLB | 5 | 1.6973 | sim |
| 06 | 3G6430A00335 | 10 | 36.6667 | **não** |
| 07 | 3G3240A07531 | 10 | 10.9793 | sim |
| 08 | S-7200-514-PAX | 10 | 1.3120 | sim |

## Implementação e testes

Novos módulos: `analysis/amendment015/age.py`, `execution.py`, `state.py`,
`references.py` e o lançador `analysis/amendment015_runner.py`.
O núcleo implementa a taxa por idade da seção 4, excesso cíclico, soma de taxas
ponderadas, controles de cauda, busca e desempate prescritos. O adaptador novo
liga essa calibração às chamadas de P1/P2_age, reutilizando as seis políticas
históricas. Os executores históricos e o manuscrito permanecem intactos.

A suíte completa passou com **212 testes em cópia isolada com histórico Git**,
incluindo as duas execuções completas do teste histórico do pipeline.
Depois da inclusão do adaptador e de suas duas travas adicionais, os
**13 testes específicos passaram na mesma cópia isolada**. A integração
numérica completa da calibração nova não foi executada: depende das nove
referências e da verificação prospectiva. Não é declarada validada.

A primeira tentativa da suíte chegou ao fim com 209 testes, uma falha e um erro:
a cópia feita com `git archive` não tinha o histórico Git consultado por dois testes.
Essa falha da preparação de testes foi corrigida usando clone isolado, sem alterar
testes históricos. Todos os logs e tracebacks da tentativa estão preservados.
Ambiente conferido: Python 3.14.0, todas as versões do lock coincidentes.

## Fontes, referências e preservação

`configuration.json` e `configuration.sha256.json` congelam fontes,
coorte, parâmetros, calendários, pesos e os nove pares sorteados com
PCG64/20261117015. O avaliador preservado é `a9_static.py`, com as operações
equivalentes de `a9_static_fast.py`; subdivisões=4, trabalhadores no máximo seis,
mais coordenador e processo de recursos; threads nativas=1.

- Concluídos: **0/9**; certificados: **nenhum**.
- Pendentes: **00–08**, com entradas congeladas e nove checkpoints individuais
  em `data/derived/a9/amendment015/references/`.
- Não existe manifesto completo de referências; nenhum limiar barato foi calculado.
- Verificação g≤0,005, perfilamento T20, ensaio técnico e principal não iniciados.
- Conferidos novamente 627 arquivos históricos, 85
  fontes congeladas, 5 entradas e nove checkpoints;
  todos os hashes conferem. Nenhum arquivo rastreado preexistente foi modificado.
- Não foram acessados ou copiados extratos de `data/raw/` ou mapas confidenciais;
  não foram abertos ganhos ou alarmes A9/A10.

## Relógios e consequências

Início global: **2026-11-18T15:57:28Z**; prazo global:
**2026-12-02T15:57:28Z** (02/12 às 12:57:28−03:00).

Início da preparação das referências:
**2026-11-18T16:16:40.223320+00:00**; prazo original do subteto:
**2026-11-19T16:16:40.223320+00:00**. Ele não reinicia em retomadas.
A recusa ocorreu depois de **3,757824 s** desse bloco, antes de qualquer busca.
O relógio continua correndo durante a parada; o ledger é a fonte do consumo vigente.

Retrato às 2026-11-18T16:18:10.952067+00:00:
consumo global **0.345264 h**;
saldo **335.654736 h**.
As durações das etapas decompõem esse consumo e não são adicionadas a ele.

Sem T20 concluída, **t71, T_base_restante e T_restante_projetado não estão disponíveis**;
o critério de escopo da seção 7 não foi avaliado. Não se infere inviabilidade
por tempo a partir do impedimento de memória nem se inicia uma subgrade.
A execução permanece parada para decisão do autor, sem contornar a alocação.

Evidências: `state.json`, `memory_preflight.json`, `time_ledger.json`,
`implementation_verification.json`, `integrity_at_stop.json` e logs no diretório
`data/derived/a9/amendment015/`.

## Retomada autorizada pelo autor — armazenamento em disco

O autor autorizou resolver o impedimento de memória sem mudança numérica. O prazo original das referências permanece 19/11/2026 às 16:16:40 UTC; a alocação permanece 17.662.817.894 bytes. Os oito contextos 00–05, 07 e 08 foram retomados com admissão pela soma das estimativas, até seis trabalhadores. Durante os testes há no máximo cinco trabalhadores de referências, coordenador, processo de recursos e processo de teste: oito processos Python. O relógio inclui o intervalo até esta retomada.

A implementação de armazenamento nova fica em `analysis/amendment015/disk.py`. Somente os vetores float64 dos kernels de calendário passam a `np.memmap`; a álgebra densa, operações, ordem, grade de ¼ de dia, tolerâncias e desempates são preservados. Rascunhos ficam em `data/derived/a9/amendment015/scratch/`, explicitamente ignorado pelo Git. Nenhum executor histórico foi alterado.

A equivalência usa dois calendários completos de aeronave, sem truncar seus 365 dias, retirados dos contextos compostos congelados 02 e 05 e com seus parâmetros e pesos reais. Esse é somente o escopo do teste de armazenamento: nenhum dos nove certificados poderá subamostrar aeronaves. Serão comparados bytes da idade e da taxa float64 e a serialização integral dos diagnósticos. O contexto 06 permanece bloqueado até os dois testes passarem e a estimativa de RAM residual/espaço em disco ser registrada e aprovada pela admissão. Nenhum limiar barato é liberado antes do manifesto completo das nove referências.

A estimativa inicial da versão em disco para o contexto 06 ficou em **2,1951 GiB de RAM residual** e **35,0675 GiB de arquivos de kernels float64**, com cerca de **688 GiB livres** no volume. Inclui as matrizes densas em RAM, temporários, cache constante e reservas explícitas; a admissão final repetirá a conferência de espaço depois dos testes. Essa previsão não libera o contexto antes da equivalência. Evidência: `disk_resource_estimate_initial.json`.

### Equivalência concluída e contexto 06 liberado para admissão

- Contexto composto 02, calendário de aeronave índice 12: idade ótima, taxa e diagnósticos integrais idênticos byte a byte. RAM 680.758259 s; disco 695.515735 s.
- Contexto composto 05, calendário de aeronave índice 13: idade ótima, taxa e diagnósticos integrais idênticos byte a byte. RAM 1107.330507 s; disco 1105.980607 s.

Os hashes das fontes conferem com `storage_extension_configuration.json`. Evidência integral: `disk_equivalence.json`; teste aprovado antes da execução de 06. A admissão final registra RAM residual de 2357015680 bytes e disco de 37653423360 bytes, com 738912632832 bytes livres e reserva adicional de 2 GiB. Ambos cabem. O coordenador publica 06 na fila e só o inicia quando a soma das tarefas admitidas couber na alocação congelada. Todos os nove certificados continuam usando os contextos compostos integrais.

## Fecho da retomada — 19/11/2026

Nova parada por RSS agregado após iniciar 07. Seis certificados preservados: 00, 01, 02, 03, 04 e 08; incompletos 05, 06 e 07. Todos os processos foram encerrados. A equivalência em disco passou nos dois testes, mas a admissão não reservava RSS retido por trabalhadores sem tarefa ativa. A salvaguarda agregada interrompeu a execução. O relato completo, as lacunas de medição e os relógios estão em `analysis/a9_amendment015_resume_report.md`. Nenhum limiar barato, verificação ou T20 foi executado; nenhum commit foi feito.
