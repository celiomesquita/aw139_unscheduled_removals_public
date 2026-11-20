# Emenda A16/A9_005 — paralelização por réplica

13/11/2026. Solicitada pelo autor durante A16, após controles nulos ×1/×2
completos e durante ×4 (502 réplicas concluídas na inspeção inicial). A decisão
decorre da capacidade ociosa do computador, não de frequências de rejeição.
Pré-registro, emendas anteriores, configuração científica congelada e resultados
concluídos são preservados. R=200, B=999, sementes, grade e critérios não mudam.

## Alteração operacional

Substituir o único processo de cálculo por um coordenador e processos de trabalho
independentes. Um processo executa uma réplica completa com as duas variantes,
chamando execute_replica do executor original, sem modificar esse código.
Paralelizar somente dentro da célula corrente: terminar todas as 200 réplicas
e avaliar a mesma barreira antes de submeter qualquer trabalho da célula seguinte.
Ordem de conclusão não entra na semente; ordenar por índice antes de inferir.

Cada processo usa um thread de BLAS/OpenMP, condicionado à verificação de
igualdade exata dos artefatos com réplicas já concluídas sob a configuração
anterior. Testar processos simultâneos em diretórios de verificação separados;
essas reproduções não contam como novas observações. Se a política de threads
alterar os resultados, não migrar com essa política. Medir aceleração em réplicas
concluídas, mantendo R e orçamento originais, sem recalcular R pelo novo tempo.

Manter todos os resumos finais, inclusive falhas. A transição interrompe somente
o processo identificado pelo PID/lock de A16, após a verificação do novo executor.
Uma réplica interrompida sem resumo final volta à fila com a mesma semente;
nenhuma réplica finalizada é substituída. Não aplicar a parada por resultados
parciais nem fazer execução especulativa entre células.

## Integridade e alterações externas

Na inspeção do workspace, paper/manuscript.tex e outros arquivos editoriais
estavam alterados externamente ao processo A16. Nenhum deles será editado,
revertido ou restaurado por esta migração. A configuração original conserva
o hash anterior do manuscrito; o manifesto operacional registra ambos os hashes.
Essa diferença documental não altera dados, ajustes ou inferência.

O novo executor continua exigindo igualdade estrita dos hashes originais de
A4/A5, dados/entradas, pré-registros, emenda de orçamento e código de cálculo.
Mudanças externas no manuscrito são registradas separadamente e não rotuladas
como “todos os arquivos protegidos inalterados”. Mudanças em qualquer entrada
ou código científico interrompem a execução. Este tratamento distingue integridade
científica de trabalho editorial concorrente, sem reescrever a configuração congelada.

Manifesto operacional separado guarda hash da configuração original, fontes do
executor paralelo, quantidade de processos, política de threads, hardware,
verificação e checkpoints preservados. Logs e heartbeats são separados por réplica;
somente o coordenador escreve estado global, relatório e resumos agregados.
