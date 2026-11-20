# Emenda 015 — fecho das referências com processos novos

**Parada no prazo original: 19/11/2026, 16:16:40 UTC. Oito referências certificadas; 06 incompleta.**
O registro do disparo é 16:16:40.001874 UTC; o fechamento do executor foi
registrado às 16:16:40.034029 UTC. Todos os PIDs do executor foram conferidos
e estão encerrados. Não houve extensão, reinício do subteto ou nova tentativa
após o corte. Nenhum commit foi realizado.

## Decisão do autor e execução

A autorização desta retomada substituiu o reaproveitamento de trabalhadores
por um processo novo para cada referência. Foram retomadas somente 05, 06 e 07;
os seis certificados anteriores ficaram intactos. A admissão usou o RSS real
agregado do coordenador e de todos os descendentes, incluindo o processo de
recursos, mais a estimativa da tarefa nova, dentro de **17.662.817.894 bytes**.
Os PIDs constam das admissões, dos checkpoints e dos registros de tarefas.

| Contexto | PID | Armazenamento | Resultado |
|---|---:|---|---|
| 07 | 878496 | RAM | certificado às 13:02:48 UTC; processo encerrado |
| 05 | 878497 | RAM | certificado às 14:26:45 UTC; processo encerrado |
| 06 | 878498 | memmap | interrompido no corte; sem certificado |

Não houve trabalhador reutilizado. O coordenador e o processo de recursos
totalizaram, com as três referências, cinco processos. Cada trabalhador saiu
ao terminar. BLAS/OpenMP/NumExpr permaneceram com um thread. A implementação
memmap de 06 é a mesma que passou nos dois testes reais byte a byte; nenhuma
operação numérica do avaliador histórico foi alterada.

Fontes e configuração desta retomada foram congeladas em
`data/derived/a9/amendment015/fresh_configuration.json`. As admissões em
`fresh_admissions/` registram o RSS agregado observado, a estimativa acrescentada,
a soma admitida, o limite e o PID. `fresh_tasks/` registra o ciclo de cada tarefa.

## Certificados concluídos

| Contexto | P/N | r | Certificado em references/ | Parede do trabalhador (h) |
|---|---|---:|---|---:|
| 00 | 3G6230A00833 | 2 | `00_certificate.json` | 2.240893 |
| 01 | 3G3240V01731 | 2 | `01_certificate.json` | 1.246330 |
| 02 | S-7200-514-PAX | 2 | `02_certificate.json` | 3.854192 |
| 03 | 3G6230A00833 | 5 | `03_certificate.json` | 2.241328 |
| 04 | 3G3240A07531 | 5 | `04_certificate.json` | 3.021360 |
| 05 | S-7200-514-PLB | 5 | `05_certificate.json` | 4.205615 |
| 07 | 3G3240A07531 | 10 | `07_certificate.json` | 2.806390 |
| 08 | S-7200-514-PAX | 10 | `08_certificate.json` | 3.444837 |

Os oito certificados foram conferidos contra os hashes dos inputs e dos
checkpoints. Os seis anteriores preservaram seus SHA-256. As durações da tabela
são diagnósticos dos trabalhadores; não são somadas ao consumo global.
Não existe manifesto completo das nove referências: ele não foi criado com
uma amostra parcial.

## Progresso de 06 no último registro antes do corte

A telemetria foi somente de leitura, por amostragem dos frames e contadores do
avaliador existente a cada 120 segundos, sem escrever em seus objetos ou mudar
a ordem das operações. O teste de controle da telemetria preservou byte a byte
a idade ótima e os diagnósticos completos do avaliador exato. O teste de fronteira
da admissão também passou. Logs: `fresh_tests.stderr.log`.

Última amostra de 06: **2026-11-19T16:16:27.871868+00:00**, aproximadamente 12,13 s antes do corte.

| Métrica | Progresso |
|---|---:|
| Fases construídas | 17,520 / 17,520 = 100% |
| Quebras de visita por fase avançadas | 11,500,435 / 17,566,720 = **65.467173%** |
| Pontos candidatos distintos já avaliados | 6,761,315 |
| Total de pontos distintos | não materializado; fração não inferida |

A fração de quebras conta as entradas finitas por fase com multiplicidade,
correspondendo aos cursores da varredura do heap. Ela não representa a fração
de idades distintas do objetivo. O registro íntegro e sua série temporal estão
em `fresh_progress/06.json` e `fresh_progress/06.jsonl`. O checkpoint de 06 registra
`interrupted`, PID 878498 e a razão do corte. Os rascunhos numéricos permanecem
em `scratch/`, fora do Git; eles não constituem certificado nem validação parcial.

## Tempos e ledger

| Medição no corte | Valor |
|---|---:|
| Parede desta tentativa | 21735.061025 s = **6.037517 h** |
| Intervalo das referências desde o início original | 86399.810297 s = **23.999947 h** |
| Consumo global C desde o commit | **24.320009 h** |
| Saldo global no corte | **311.679991 h** |

O início original foi 2026-11-18T16:16:40.223320Z e o corte solicitado foi
2026-11-19T16:16:40Z. O subteto permaneceu o mesmo, incluindo as pausas e
as tentativas anteriores. Esta tentativa é parte desse intervalo; não é
acrescentada novamente a ele nem a C. O relógio global continua sendo o tempo
corrido desde `2d7e19d`, 2026-11-18T15:57:28Z, com prazo em 2026-12-02T15:57:28Z.

O ledger foi atualizado no fecho da auditoria às **2026-11-19T16:45:42.725526+00:00**:
C = **24.804090 h** e saldo =
**311.195910 h**. A espera e a auditoria após o corte
entram nesse consumo global. O bloco fechado, com a duração e os valores no
corte, está em `time_ledger.json/reference_cutoff_outcome`. O campo legado
`reference_consumed_seconds` segue medindo o intervalo desde a preparação;
a duração fechada do executor é registrada separadamente para não confundir
essa espera com cálculo após o prazo.

## Integridade e parada para auditoria

Foram reconferidos 627 arquivos históricos, 85 fontes originais congeladas,
as fontes da versão memmap e da retomada, os oito certificados e os respectivos
inputs/checkpoints. Todos os hashes conferem. Evidência: `fresh_integrity.json`.
Os testes específicos passaram; nenhuma precisão, tolerância, amostra,
semente, parâmetro, peso, grade, política ou R foi reduzido. Fontes históricas,
pré-registros, artefatos antigos e manuscrito permanecem intactos.

A condição de nove referências certificadas não foi satisfeita até o prazo.
**A calibração não foi validada. Nenhum limiar barato, verificação g≤0,005,
perfilamento T20, ensaio técnico ou execução principal foi iniciado.**
A execução permanece parada, sem manifesto parcial declarado completo.
`fresh_final_summary.json` reúne o estado, as frações, os tempos e as provas
para a auditoria do autor.
