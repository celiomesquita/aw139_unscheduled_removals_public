# Pré-registro A5 — validação temporal e escolha da escala A2

Estado: **protocolo escrito; execução de A5 não iniciada; aguarda commit do autor**.
Autorização e ponto de parada: `tarefas_codex.md`, T3 e “Ordem e critério de parada”.
Data de redação: 12/11/2026. Versão: A5_v1. Semente: 20261112.

## Pergunta, população e alcance

K2 pergunta se a dependência da idade melhora a previsão de **remoção não
programada registrada** frente à taxa constante da frota. Não se exige confirmar
falha funcional, identidade física e instante da detecção nos documentos completos.
T1 encerrou A3.1 com resultado inconclusivo; A3.2 é trabalho futuro.

População: trechos com instalação observada dentro de 01/01/2024–31/03/2026,
incluindo os removidos e os ainda em serviço, sem unidades pré-2024. A população
de risco é formada pelas unidades desses trechos, não pelo total da frota.
Predições referem-se às unidades em risco na origem; não incluem unidades que
serão instaladas depois da origem nem suas futuras remoções.

Candidatos de K1: os 11 P/N retidos em `data/derived/k1_candidates.csv`.
K1 usou a janela completa, e os dados já foram examinados em análises exploratórias.
Portanto este documento fixa a análise antes de sua execução, mas não constitui
pré-registro anterior ao acesso aos dados nem validação externa da seleção de P/N.
K2 é condicionado a essa seleção; declarar o risco de seleção retrospectiva.

## Tempo, informação disponível e ajuste

Origens: primeiro dia dos meses 2025-01 a 2025-12. Corte: fim do dia anterior à
origem. Horizontes: até a mesma data 1, 2 e 3 meses depois da origem, sem exceder
o fim da janela. Unidade em risco: instalação anterior à origem e nenhuma remoção
até o corte. Uma remoção no dia da origem pertence ao período de previsão.

Em cada ajuste expansivo, recortar todos os trechos na data de corte. Remoção
posterior ao corte vira censura administrativa nesse corte, sem usar motivo,
instante ou exposição posteriores. Instalações posteriores não entram. Modelo,
seleção de escala, parâmetros de utilização e imputação são recalculados somente
com informação disponível no treino.

O extrato não fornece data de inserção no sistema: assume-se que a instalação
estava disponível na data registrada. Não interpretar esse pressuposto como
prova da disponibilidade histórica do registro. Sensibilidade adicional de
proveniência: usar somente instalações ligadas a registros de substituição já
existentes até o corte; informar cobertura sem escolher retrospectivamente o
resultado mais favorável.

Ajuste por máxima verossimilhança, com remoções programadas/outras como censuras
do processo específico não programado e trechos em serviço censurados no corte.
Principal: idades exatas registradas, evitando o intervalo diário degenerado de A2.
Sensibilidade: limites aproximados do mapa T2, reconstruídos com tarefas anteriores
ao corte, sem reutilizar ajuste da janela completa. Nunca comparar AIC de
densidades em FH, calendário e decolagens para escolher escala.

Idade de exposição zero em uma remoção não permite densidade Weibull exata:
registrar a ocorrência e não adicionar epsilon nem imputar exposição positiva.
Tal registro não entra no ajuste dessa escala, mas continua nos dados de avaliação
e nas outras escalas identificáveis. Expor contagens por P/N/origem/escala. Com
menos de cinco eventos válidos ou ajuste sem convergência/parâmetros finitos,
essa previsão usa a linha de base da frota e recebe marcador de fallback; não
se eliminam silenciosamente seus casos de avaliação.

## Modelos, riscos concorrentes e previsão

Comparar: (a) Weibull por P/N em FH, calendário e decolagens; (b) exponencial por
P/N nas mesmas escalas; (c) intensidade constante agrupada da frota, estimada
somente na coorte principal dos candidatos K1, em unidades-dia em risco.
O denominador da linha de base nunca é a exposição de toda a configuração instalada.

Na ausência de remoção concorrente, a probabilidade condicionada à idade é
1 − S(idade + exposição futura)/S(idade). Uma remoção programada antes do horizonte
retira a unidade: não é um negativo observado da vida latente após essa retirada.
Para o endpoint operacional, tratar outras remoções como riscos concorrentes.
Estimar uma intensidade concorrente constante por P/N em dias de risco no treino
e aplicá-la igualmente aos modelos (a), (b) e (c). Integrar a incidência acumulada
de remoção não programada até o horizonte, combinando o risco específico previsto
com a sobrevivência à remoção concorrente. Se faltar informação por P/N, usar a
intensidade concorrente agrupada da coorte de treino, com marcador explícito.
Assim, a avaliação é do primeiro desfecho por unidade sob a política observada,
sem inventar uma vida física após remoção preventiva.

Exposição futura principal: taxa diária da aeronave nos 90 dias anteriores à
origem, aplicada ao número de dias do horizonte. Calendário usa dias decorridos.
As mesmas taxas são usadas pelos modelos comparados. Sensibilidade: FH realizadas
no horizonte, identificadas como programação conhecida/informação futura; nunca
misturar seu resultado com o principal. Valores de horas ausentes têm cobertura
explicitada; não se apresentam como voos conhecidos. Sem taxa utilizável, fallback
para previsão em calendário e marcador de indisponibilidade de exposição.

Decolagens: principal com histórico de contadores completo desde a instalação até
o corte; exposição futura estimada nos 90 dias anteriores. Não imputar no principal.
Nos casos não elegíveis, a estratégia dessa escala usa a mesma previsão (c), com
marcador, para conservar a população de avaliação. Informar separadamente a
comparação restrita aos casos completos. Sensibilidade: imputar contagens ausentes
pela razão decolagens/FH da aeronave na janela de treino, usando somente linhas
com ambos preenchidos e FH positivas. Sem razão identificável, continuar ausente.

Somar probabilidades por P/N × aeronave × origem × horizonte para contagem esperada.
Guardar também previsões individuais para Brier/log score Bernoulli. O indicador
observado vale 1 se houver remoção não programada da unidade até o horizonte;
vale 0 se não houver, inclusive quando uma remoção concorrente encerra o trecho.
Fim administrativo deve cobrir o horizonte; não converter censura administrativa
anterior em negativo. As origens escolhidas têm horizontes completos no extrato.

## Escolha da escala e métricas

Escolher a escala por desempenho preditivo, não pelo AIC diário. Para evitar
escolher e testar a melhor escala nos mesmos alvos, usar seleção temporal interna:
para cada origem externa, avaliar origens mensais internas a partir de 2024-07,
somente com horizontes cujo término seja anterior à origem externa. Cada origem
interna também tem treino expansivo recortado. Escolher por P/N a escala Weibull
com maior log score médio interno, sobre os mesmos casos, incluindo fallbacks.
Sem avaliação interna válida, usar calendário e registrar o motivo. Empate numérico
(diferença absoluta ≤ 1e-8): manter FH, depois calendário, depois decolagens.
A exponencial por P/N terá seleção interna própria sob a mesma regra. Produzir
também os escores externos separados por escala; a preferência retrospectiva sobre
os 12 meses externos será apenas descritiva, sem redefinir K2.

Log score principal: média de y log(p) + (1−y) log(1−p), maior é melhor. Usar
clipping apenas numérico a [1e-12, 1−1e-12] para calcular logaritmos; preservar
probabilidades originais nos artefatos. Brier: média de (p−y)², menor é melhor.
Calibração: observado/esperado por decil de risco, com número de unidades,
observados e esperados; esperado zero fica indefinido, não convertido em zero.
Decis definidos por ordenação determinística com desempate pelo ID do trecho.

Agregação para K2: calcular diferenças pareadas por unidade, média dentro de
aeronave/origem/horizonte e depois média dos horizontes, origens e aeronaves
com dados, para impedir que a aeronave mais utilizada seja uma réplica adicional.
Relatar também resultados por P/N. Toda comparação usa os mesmos casos; fallback
conserva a cobertura e seu percentual será informado por modelo e origem.

Incerteza: bootstrap em blocos de aeronave, 10 000 reamostragens, gerador PCG64,
semente 20261112, preservando juntos trechos, origens e horizontes da aeronave.
IC 95% percentil da diferença Weibull − (c) do log score. Replicações sem casos
de um P/N não geram diferença zero; são ausentes e sua frequência é informada.
Para decisões por P/N, informar IC individuais e intervalos simultâneos com
Bonferroni (11 comparações), evitando escolher só resultados positivos ocasionais.

## Critério K2 e sensibilidades obrigatórias

- **Favorável:** limite inferior do IC 95% agregado de Weibull − (c) acima de zero.
- **Mista:** agregado não favorável, mas pelo menos um P/N com limite inferior
  simultâneo acima de zero; restringir a esses P/N.
- **Nula:** demais casos; acionar A4 (modelo hierárquico), sem reformular previamente
  o estudo para encerrar o trabalho. Parar e informar o autor.

Brier e calibração qualificam o resultado e são sempre relatados, mesmo quando
discordam do log score. A comparação Weibull–exponencial identifica a contribuição
da idade; um resultado de K2 favorável não prova que re-estimar mensalmente melhora
o custo da política nem que os parâmetros sejam uma lei de vida física transferível.

Sensibilidades fixadas: exposição FH realizada; decolagens imputadas pelo treino;
intervalos operacionais T2; proveniência da instalação; e exclusão dos quatro
registros de correção administrativa R00173, R00293, R00294, R00328, preservados
em `adjudication_status.csv`/`extended_review_results.csv`. Na exclusão, remover o
trecho da análise de sensibilidade, sem converter seu evento em censura independente.
Aplicar a mesma exclusão ao treino e avaliação, com rastreio por chave completa
(P/N, serial, aeronave, instalação e remoção), não por posição de linha.

## Testes e artefatos antes de divulgar resultados

Testes a implementar antes de rodar A5: evento posterior à origem não altera ajuste
do passado; probabilidades em [0,1] e monótonas no horizonte; dados simulados com
beta=1 não mostram ganho sistemático de Weibull sobre exponencial (IC da diferença
compatível com zero), e com beta=3 mostram ganho positivo com amostra suficiente;
concorrentes impedem prever remoção depois da saída; ausência de decolagens não
elimina a avaliação dos demais modelos; determinismo em duas execuções completas.
Esses testes científicos de A5 ainda não foram executados; testes do documento
somente verificam o contrato escrito. Nenhum resultado K2 é apresentado aqui.

Artefatos previstos: ajustes por origem/escala, cobertura e fallbacks, predições
por unidade, contagens por P/N/aeronave/horizonte, escores pareados por aeronave,
calibração, replicações bootstrap, sensibilidades e decisão K2. Exportar somente
identificadores anonimizados, códigos, números e hashes, sem texto livre do operador.
Registrar versões e hashes dos insumos no manifesto de execução.

## Parada obrigatória

O autor deve fazer commit deste arquivo antes da execução de A5. O agente não
faz commit. O hash e a revisão Git do pré-registro serão registrados na execução.
Qualquer alteração posterior exige emenda datada antes de nova análise, sem
reescrever silenciosamente a versão que orientou os resultados.
Não iniciar A7 nesta rodada. T5 será retomada após este ponto de parada.
