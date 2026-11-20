# Emenda 015 — retomada autorizada e nova parada de memória agregada

**STOP em 2026-11-19T02:41:48.945356+00:00. Seis referências certificadas; três incompletas.**
A execução foi interrompida pela salvaguarda de RSS agregado ao iniciar 07.
Todos os processos do executor foram conferidos e estão encerrados.
Não houve commit, calibração barata, verificação de g, T20, ensaio técnico
ou execução principal. Ganhos e alarmes A9/A10 não foram abertos.

## Autorização e solução do primeiro impedimento

O autor autorizou iniciar 00–05, 07 e 08 em RAM por admissão, enquanto a
solução em disco de 06 era implementada e testada. O orçamento global continua
336 h desde `2d7e19d`, em 2026-11-18T15:57:28Z, até 2026-12-02T15:57:28Z.
O subteto das referências conservou o instante inicial
2026-11-18T16:16:40.223320Z e o prazo original de 19/11 às 16:16:40 UTC.
Nenhum relógio reiniciou. A alocação permaneceu **17.662.817.894 bytes**.

Foram usados no máximo seis trabalhadores, mais coordenador e processo de
recursos. Durante a equivalência houve no máximo cinco trabalhadores de
referências, para reservar o oitavo processo ao teste. BLAS/OpenMP/NumExpr
ficaram com um thread por processo. Parede e CPU são registradas separadamente;
o consumo global não soma CPU, durações de trabalhadores ou intervalos paralelos.

A implementação `analysis/amendment015/disk.py` preserva o construtor e os
métodos aritméticos do avaliador histórico otimizado. Só os seis vetores dos
kernels passam a `np.memmap`, em float64, sem alteração de valores, ordem,
grade de ¼ de dia, caudas, estacionariedade ou desempates. As matrizes da
álgebra linear ficam em RAM. Os rascunhos estão em
`data/derived/a9/amendment015/scratch/`, ignorado pelo Git.
Os executores históricos e a configuração inicial permanecem intactos.

## Equivalência em dois calendários reais congelados

Os testes usaram calendários completos de aeronave, cada um com seus 365 dias,
parâmetros e pesos da amostra congelada: índice 12 do contexto composto 02 e
índice 13 de 05. Este é o escopo do teste de armazenamento. Todos os certificados
usam o contexto composto integral, com todas as aeronaves e pesos, sem subamostra.

| Contexto / índice | RAM (s) | Disco (s) | Idade byte a byte | Taxa byte a byte | Diagnósticos byte a byte |
|---|---:|---:|---|---|---|
| 02 / 12 | 680.758259 | 695.515735 | sim | sim | sim |
| 05 / 13 | 1107.330507 | 1105.980607 | sim | sim | sim |

Os dois testes passaram antes de liberar 06. Os bytes float64 da idade e da
taxa e a serialização integral dos diagnósticos foram iguais. Resultados,
hashes e entradas estão em `disk_equivalence.json`; fontes/configuração da
extensão estão em `storage_extension_configuration.json`. Seus hashes foram
reconferidos após a parada.

A admissão de 06 foi precedida da estimativa de **2357015680 bytes
(2.195142 GiB) de RAM residual** e
**37653423360 bytes (35.067483 GiB) em disco**,
com 738912632832 bytes livres e reserva adicional de 2 GiB.
Ambos cabiam. Evidência: `disk_resource_preflight.json`.
O checkpoint registra o início de 06 em disco às 2026-11-18T21:03:08.559976Z.
Os rascunhos permanecem preservados; não constituem certificado de conclusão.

## Seis certificados preservados

| Contexto | P/N | r | Parede do trabalhador (h) | CPU user+system (h) |
|---|---|---:|---:|---:|
| 00 | 3G6230A00833 | 2 | 2.240893 | 2.215107 |
| 01 | 3G3240V01731 | 2 | 1.246330 | 1.238229 |
| 02 | S-7200-514-PAX | 2 | 3.854192 | 3.845268 |
| 03 | 3G6230A00833 | 5 | 2.241328 | 2.215392 |
| 04 | 3G3240A07531 | 5 | 3.021360 | 3.019184 |
| 08 | S-7200-514-PAX | 10 | 3.444837 | 3.443401 |

Os seis certificados tiveram SHA-256 e compatibilidade com os respectivos
inputs/checkpoints conferidos. As durações desta tabela são diagnósticas;
não são somadas ao consumo global nem usadas como tempo de réplica T20.
Incompletos: **05 (RAM), 06 (memmap) e 07 (RAM)**. Seus checkpoints foram marcados
`interrupted_memory`; as versões anteriores, com `running`, ficaram preservadas
em `*_checkpoint_before_aggregate_stop.json`. Nenhum resultado incompleto foi
convertido em referência. Não há manifesto completo das nove referências.

## Nova falha: lacuna na admissão por memória agregada

Código: `AGGREGATE_RSS_EXCEEDS_FROZEN_ALLOCATION`.
A admissão que implementei somava as estimativas das **tarefas ativas**, mas
não reservava o RSS ainda retido pelos processos que já tinham concluído suas
tarefas. A verificação de RSS agregado era separada e incluía todos os processos.
Ao admitir 07 após a conclusão de 04, a soma real ultrapassou a alocação e essa
salvaguarda interrompeu o executor. Isso expõe uma lacuna da admissão implementada.
Não houve divergência nos testes numéricos de armazenamento.

A última amostra persistida, anterior ao disparo, foi de
**17490120704 bytes
(16.288944 GiB)**; ela inclui trabalhadores
com aproximadamente 9,51 e 3,98 GiB. A associação explícita entre tarefa e PID
não foi gravada. O valor exato da amostra que excedeu a alocação **não foi
persistido**, porque a exceção precedia a escrita do progresso. Ele está
registrado como ausente, sem inventar pico nem usar zero. A análise da lacuna
vem do código de admissão e das amostras; não certifica atribuição de cada
parcela retida a uma tarefa específica.

Evidências: `state.json`, `resume.stderr.log`, `memory_stop_summary.json`,
`reference_progress.json` e `reference_resource_history.jsonseq`.
O histórico periódico de RSS começou somente às 00:18 UTC de 19/11; a lacuna
anterior não foi preenchida artificialmente. Checkpoints e todos os rascunhos
ficaram em disco. Não houve nova tentativa após essa parada técnica.

## Integridade e estado do restante

Após a parada foram reconferidos **627 arquivos históricos**, **85 fontes
congeladas**, quatro fontes da extensão, nove inputs/checkpoints e seis
certificados: todos os hashes conferem. Configuração inicial, fontes históricas,
pré-registros, artefatos antigos e manuscrito estão intactos. A única alteração
rastreada preexistente é a regra de `.gitignore` para os rascunhos; código e
saídas novos permanecem sem commit. Evidência: `integrity_after_resume_stop.json`.

Há código prospectivo separado para a verificação e o perfilamento, com fontes
registradas, mas essas etapas **não foram executadas**. Não há validação parcial.
Sem T20 completa, t71, T_base_restante e T_restante_projetado estão indisponíveis;
o critério de escopo da seção 7 não foi avaliado. Células, políticas, R, amostra,
semente, parâmetros, pesos e precisão não foram reduzidos.

## Retrato dos relógios no fecho

Atualização UTC: **2026-11-19T02:48:14.378922+00:00**.

- Consumo global C: **10.846216 h**.
- Saldo global: **325.153784 h**.
- Saldo do subteto original: **13.473846 h**.
- Prazo das referências: **2026-11-19T16:16:40Z**, sem reinício.
- Prazo global: **2026-12-02T15:57:28Z**.

Os relógios continuam correndo durante a parada. O ledger conserva a decisão
do autor, o primeiro impedimento, esta nova parada e o consumo calculado pelo
intervalo desde o commit. A execução permanece parada com seis certificados
preservados e três contextos incompletos.

## Nova autorização — processos descartáveis e telemetria (19/11/2026)

O autor autorizou retomar somente 05, 06 e 07, com corte em 2026-11-19T16:16:40Z, preservando os seis certificados. Cada referência usa um processo novo, encerrado ao terminar. A admissão considera o RSS agregado real do coordenador e de todos os descendentes mais a estimativa da tarefa nova, sem ultrapassar 17.662.817.894 bytes. Não há reaproveitamento de trabalhadores. 07 e 05 usam RAM; 06 usa a versão memmap anteriormente testada.

Entradas de admissão e PIDs ficam em `fresh_admissions/`, execução por tarefa em `fresh_tasks/` e configuração/fontes em `fresh_configuration.json`. A nova telemetria lê os frames e contadores do avaliador existente a cada 120 s; não escreve em objetos do cálculo. Ela registra fases construídas e entradas finitas de quebra por fase (com multiplicidade), além do contador de pontos candidatos distintos já avaliados. O total de pontos distintos não é materializado; sua fração não é inventada. Os resultados ficam em `fresh_progress/`.

Dois testes específicos passaram: fronteiras da admissão com RSS retido e identidade byte a byte da idade/diagnósticos do avaliador exato com e sem o observador num caso pequeno de controle. Fontes históricas e versão memmap testada permanecem intactas. Mesmo se as nove referências forem certificadas, o manifesto será congelado e conferido e a execução parará antes de g≤0,005 para auditoria do autor; a verificação e a T20 não estão autorizadas nesta retomada.

## Fecho da retomada com processos novos

Em 19/11/2026, o corte original de 16:16:40 UTC foi cumprido. 05 e 07 concluíram; 06 ficou incompleto. Oito certificados foram preservados e conferidos. A última telemetria de 06 registrou 100% das fases e 65,467173% das quebras por fase varridas, com multiplicidade. Não houve validação parcial, limiar barato, verificação g ou T20. O relato e os relógios do corte e da auditoria estão em `analysis/a9_amendment015_fresh_report.md`.
