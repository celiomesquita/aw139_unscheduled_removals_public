# Emenda A16/A9_013 — operações equivalentes e novo executor do piloto

14/11/2026. Implementação da otimização autorizada pela emenda 012. Posterior
à interrupção do piloto original, sem abertura de ganhos/alarme e anterior
a observações avaliadas do novo executor. Métodos, grade, mínimo R=200,
sementes, aquecimento, censuras e tolerâncias científicas permanecem os mesmos.

## Identidades numéricas e busca de P1

Preservar todos os pontos de mudança de visita e o critério de refinamento da
emenda 011. Atualizar somente as probabilidades acrescentadas entre duas
visitas, em vez de reconstruir sempre o prefixo inteiro. Recalcular o prefixo
periodicamente para controlar erro acumulado. A inversa recebe atualização
de posto um in-place; produtos com diferenças esparsas não percorrem zeros.
Taxas de calendários não alterados são reutilizadas sem recalcular o produto.

Recalcular a inversa a cada 8 192 atualizações ou antes, se necessário. A cada
128, conferir a equação estacionária com tolerância interna de 1e-10, mais
estrita que a verificação científica de 1e-7. Permanecem as verificações de
normalização, positividade e denominador. A periodicidade da operação muda,
não os critérios de aceitação ou os resultados exigidos.

Na ausência de concorrência, usar as expressões analíticas Weibull de massa
e primeiro momento, pela gama incompleta. Com concorrência constante, usar
as identidades C=ν∫S(t)dt, U=S(início)−S(fim)−C e momento da primeira renovação
=∫S(t)dt−duração×S(fim). Incremento operacional zero tem integral exponencial
exata. Refinar quadratura nas demais células e manter a coordenada de
probabilidade original como fallback em células rígidas ou sem precisão
suficiente. Checagens internas são mais estritas; não se relaxam as tolerâncias
de massa, duração, custo, grade temporal ou convergência do protocolo.

Relógios constantes compartilham kernels imutáveis. A idade corrente de uma
unidade nunca é compartilhada por esse cache. Na previsão, somente a matriz
de renovação com relógio/parâmetros/precisão idênticos é reutilizada entre
unidades da mesma decisão; o custo condicionado à idade continua individual.

## Paralelização e memória

Até seis processos de calibração, uma thread numérica nativa por processo.
P/N e grades numéricas são cálculos independentes; a ordem de retorno não
altera a ordenação científica. As grades 1/2/4 e suas regras de aceitação são
idênticas ao executor serial. A fila pondera uma estimativa das matrizes e
kernels por grade para limitar memória; não reduz P/N, fases, cauda ou precisão
para caber na máquina. Uma grade que não caiba é uma falha explícita de recurso.
Monitorar pai e filhos, registrando memória agregada amostrada e CPU disponível;
lacunas de amostragem não recebem duração inventada.

## Equivalência e diretórios

A versão original completa e a réplica parcial estão preservadas. Antes da
retomada, exigir o mesmo limiar escolhido e o mesmo percurso de pontos de
mudança em controles completos; comparar matrizes/taxas com erro muito inferior
às tolerâncias científicas. Exigir identidade dos eventos, custos, alarmes e
parâmetros dos fluxos artificiais completos das seis políticas contra os
artefatos preservados, além de determinismo serial/spawned. Arredondamentos de
álgebra equivalentes não são apresentados como igualdade de bytes.

Novo diretório: data/derived/a9/pilot_optimised/. O piloto original em pilot/
não é reescrito. As cinco sementes são as mesmas; o aquecimento já materializado
é reutilizado pelos hashes, sem novo sorteio. Não usar benchmarks de subetapas
como medições completas nem para selecionar R.

## Orçamento e interrupção autorizada

O limite total continua 120 h. Congelar um ledger dos tempos anteriores
registrados, sem duplicar provas copiadas e com lacunas explícitas. Descontar
esses tempos e os novos tempos do piloto da disponibilidade usada na mesma
fórmula de 72 células, reserva 1,5 e múltiplos de 50. Não reiniciar o orçamento
nem aumentar R por ignorar o custo anterior.

As cinco medições completas continuam necessárias para fixar R. Se uma medição
completa, sozinha, já demonstrar que nenhum conjunto de cinco comportará R≥200,
aplicar a interrupção por inviabilidade autorizada na emenda 012: preservar a
medição, não selecionar R e não gastar as outras quatro sem nova decisão de
orçamento. O mesmo vale para esgotamento do orçamento restante. Essa regra
usa somente custo computacional, sem testes de significância ou resultados
de políticas, e não declara concluído o piloto. A execução principal nunca
é iniciada automaticamente.
