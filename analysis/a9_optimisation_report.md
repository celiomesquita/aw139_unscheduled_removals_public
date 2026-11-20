# A9/A10 — interrupção autorizada e otimização equivalente

14/11/2026. Emenda 012 autorizada explicitamente pelo autor. O processo
original PID 15052 foi conferido por comando, diretório e configuração e
terminado às 22:19:35 UTC. Nenhum outro processo de trabalho foi encerrado.
Preservados o estado anterior, logs, configuração, fontes, história auxiliar
e réplica parcial. Foram 1 280,389 s de parede e 1 261,656 s de CPU, com zero
réplicas completas e R indefinido. O tempo não foi descartado do orçamento.

## Mudanças de execução

P1 mantém todos os pontos de mudança de visita e os mesmos critérios de
convergência. A implementação atualiza diferenças de linhas em vez de repetir
prefixos, usa produtos esparsos e atualização de posto um in-place, e verifica
o resíduo estacionário antes de aceitar a reutilização da inversa. A montagem
usa identidades de massa/momento e o integral de sobrevivência, com fallback
para a quadratura original quando necessário. Relógios constantes compartilham
kernels imutáveis; idade corrente e estado estocástico continuam individuais.

Os kernels de previsão idênticos são reutilizados somente dentro da mesma
decisão, com chave completa de relógio, parâmetros e precisão. Calibrações
independentes de P/N/grade podem usar até seis processos, com fila limitada
por memória. Não se reduzem fases, cauda, P/N ou precisão para caber na RAM.
Pai e filhos têm CPU e memória amostradas, com lacunas explicitadas.

## Equivalência e desempenho medido

Os testes completos mantiveram o limiar escolhido, número de pontos de busca,
matrizes e taxas dentro de limites muito inferiores às tolerâncias científicas.
As diferenças de álgebra não são chamadas de igualdade de bytes. Na comparação
anual das mesmas entradas do piloto salvo, 8 192 atualizações tiveram:

| Trecho | Original, s | Otimizado, s |
|---|---|---|
| Montagem | 19,205019 | 0,562782 |
| Atualizações | 5,700540 | 0,418279 |
| Total medido | 24,905560 | 0,981061 |

Aceleração desse trecho: aproximadamente 25,4×. Diferença máxima na matriz
de probabilidades: 5,04e-16; na distribuição estacionária: 5,47e-15; na taxa
esperada: 3,63e-16. Isso não mede a calibração global nem uma réplica completa
e não fixa R. Versões intermediárias e medições anteriores foram preservadas.

Os doze percursos completos artificiais das seis políticas mantiveram
exatamente eventos, custos, alarmes e parâmetros em relação à versão
preservada. A execução serial e a spawned também coincidiram. A suíte completa
passou com 182 testes, zero erros/falhas. Esses controles artificiais não são
resultados de ganho da frota. Provas em data/derived/a9/optimisation/verification.json
e kernel_benchmark.json. O manuscrito e os resultados científicos anteriores
não foram alterados.

## Retomada e orçamento

Emenda 013 e fontes congeladas antes da retomada. Novo diretório:
data/derived/a9/pilot_optimised/. Configuração SHA-256
5b4c65cfdd0e7b4d29d4921680bfb5d3bb8763e5e7d3b28db428140d062bdb94.
Início: 22:58:40 UTC de 14/11/2026, 19:58:40 de São Paulo, PID 34396.
Até seis processos de calibração, uma thread nativa por processo. As sementes
são as mesmas e o aquecimento já salvo é reutilizado, sem novo sorteio.

O ledger de custos anteriores registra 2 825,432 s conhecidos, sem duplicar
provas copiadas. Há custos antigos não medidos, explicitados sem imputação;
a disponibilidade de cerca de 119,215 h é um limite superior antes do novo
piloto. Os novos tempos serão descontados, sem reiniciar as 120 h.

As cinco réplicas completas continuam necessárias para fixar R. Se uma réplica
completa já provar a impossibilidade de R≥200, a execução para por certificado
computacional autorizado, preserva essa medição e não seleciona R. Não se
gastam as outras quatro nem se inicia a rodada principal sem decisão de
orçamento. A aceleração do kernel não é promessa de caber nas 120 h.

## Estado vigente em 15/11/2026

O piloto otimizado foi interrompido por autorização expressa, sem completar a
réplica 0. Os estados de retomada acima são históricos.
[Decomposição](a9_partial_time_decomposition.md) e
[emenda 014 proposta](emenda_A16_A9_014.md): orçamento não reiniciado, saldo
máximo 95,049470 h após a conferência debitada, nenhuma nova execução e R indefinido.
