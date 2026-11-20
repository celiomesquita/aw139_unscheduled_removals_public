# Emenda A16/A9_007 — execução de T15/T16 após commit da correção

13/11/2026. Pré-registros e emendas 001–006 preservados. A emenda 006 foi
commitada em 6848e19 e o autor autorizou T15/T16. Estas convenções precedem
qualquer resultado real corrigido ou controle novo com fluxo 17.

## Reutilização e separação dos artefatos

T15 usa os adaptadores commitados da emenda 006, com as mesmas variantes,
origens, seleção interna, estimação, métricas e bootstrap de cada estudo.
Resultados de 30 dias ficam na raiz de a5_errata/a4_errata; 60 dias ficam
em minimum_60_days/. Não executar os mains que escrevem nas pastas históricas.

O treino não depende da taxa prevista, como verificado em T14. Assim, dentro
da mesma variante/origem, pode ser reutilizado entre os limiares 30/60 dias.
Não compartilhar treino entre origens, variantes com observações diferentes,
réplicas ou estudos. A seleção interna de A5 é recalculada para cada limiar.
Salvar ajustes comuns identificados como tal. Reproduzir duas execuções
completas da errata e exigir igualdade integral de realized_fh com o original.

T16 usa diretório próprio data/derived/a16/flow17/, separado dos 600 controles
antigos em power/. O executor reutiliza a função original execute_replica,
injetando, somente no processo de trabalho, o adaptador corrigido e a chave de
fluxo 17. O cache entre principal/realized_fh na mesma origem permanece o da
emenda 002. Grade, R=200, B=999 e barreira não mudam. Nenhum dado de errata
entra nos parâmetros verdadeiros, que continuam vindo de A4 original.

## Sensibilidade de 60 dias em A16

Antes das réplicas, comparar os dias disponíveis em todas as aeronaves/origens
externas de A16. Se os indicadores D≥30 e D≥60 e as taxas disponíveis forem
idênticos, as duas regras geram as mesmas previsões e inferência para qualquer
realização de eventos sob esses relógios. Registrar essa equivalência funcional,
sem contabilizar uma segunda amostra independente. Se houver janela divergente,
executar a sensibilidade separadamente, sem escolher o limiar pelos resultados.
Essa verificação não dispensa a sensibilidade completa de A5, cujas origens
internas podem conter outras janelas, nem antecipa equivalência em A9.

## Telemetria e falhas

A variante antiga null_x4/187/realized_fh falhou por PermissionError em gravação
de heartbeat, não por erro do estimador. Ela continua preservada como falha.
Na execução nova, repetir somente a gravação atômica do mesmo payload após
PermissionError transitório; nunca repetir um ajuste ou sorteio para substituir
uma falha. Se o heartbeat continuar indisponível, registrar o incidente e seguir
o cálculo, pois o estado de progresso não é dado científico. Falha definitiva
na gravação de resultados/checkpoint continua sendo erro de execução rastreável.

## Integridade, orçamento e processos

Configurações próprias, com hashes, precedem as execuções. Conferir todos os
artefatos históricos, relatórios, pré-registros, emendas anteriores e parâmetros
do gerador. Alterações editoriais externas são registradas separadamente, como
na emenda 005; o manuscrito não é editado por T15/T16.

Somar tempos já registrados do piloto e dos controles antigos aos novos tempos.
Conservar tempo de parede e soma dos tempos de processos separadamente; indicar
registros faltantes sem inventar duração. Não zerar o orçamento de 60 h de A16
ou recalcular R após a aceleração. Excedente é registrado sem parada opcional.

T15 e T16 podem executar em paralelo, com número limitado de processos e um
thread por biblioteca numérica. Resultados da errata não alteram a configuração
de A16. A barreira de cada célula nula completa governa T16; nova falha implica
parada e comunicação, sem outra correção. A9/A10 não são lançadas pelo executor.
