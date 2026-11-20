# Emenda A4_001 — implementação antes da execução

Pré-registro original preservado: A4_v1, commit dd49dab, famílias 7/2/2 por
mecanismo; log beta global. Data: 12/11/2026. Nenhum resultado A4 calculado.

## Convenções numéricas

Verossimilhança marginal por Laplace, Hessianas analíticas em log beta/log eta.
Modos condicionais ajustados conjuntamente em vetor por L-BFGS-B, com gradiente
analítico. Hiperparâmetros por L-BFGS-B com diferenças finitas, quatro inícios
(mu_beta = log 1/log 2; desvios 0,25/1), mais ajuste agrupado de variância zero.
As fronteiras zero individuais são avaliadas explicitamente; a melhor solução
finita convergida entre tentativas é retida. A seleção usa somente treino.
Variância zero fixa exatamente o efeito na média e reduz a dimensão integrada.

Os controles de 2 000 iterações e tolerância de objetivo 1e-8 do protocolo
permanecem. Modelos sem convergência/curvatura válida não recebem aprovação
por terem objetivo finito: geram fallback com código. Não se usa ajuste MAP
conjunto dos hiperparâmetros, que teria degenerescência na variância zero.

Teste de recuperação: 11 P/N, 1 000 unidades por P/N, semente 20261112,
beta global em torno de 2, dispersão log beta 0,25, dispersão log eta 0,35,
censura administrativa a 800 unidades de exposição. Comparar efeitos aos valores
gerados e hiperparâmetros aos momentos dos efeitos realizados: tolerâncias 0,20
para média log beta, 0,25 para médias log eta e 0,25 para desvios. Configurações
uma família e 7/2/2. Não equivale a precisão populacional com duas famílias pequenas.

## Proveniência A5

Correção operacional autorizada na nota T7: manifesto original A5 preservado
integralmente a partir de analysis/audit/a5_initial_manifest.json. A revisão de
novas reproduções vai para pipeline_manifest.json. O protocolo A5, seu resultado
K2 e seus CSV numéricos não são alterados por essa correção.
