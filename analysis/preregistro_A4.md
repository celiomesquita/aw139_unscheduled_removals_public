# Pré-registro A4 — encolhimento hierárquico e valor preditivo da idade

**Desenho fixado depois de ver A5: detalhes pós-hoc.** A4 era o caminho
pré-especificado para K2 nulo; sua escala, estrutura e comparadores específicos
foram definidos após o diagnóstico de A5. O artigo deve apresentar essa
temporalidade, sem tratar A4 como confirmação independente ou apagar K2 nulo.

Versão: A4_v1, 12/11/2026 (famílias por mecanismo e nível global de beta
definidos pelo autor antes do commit e de qualquer execução). Estado: **protocolo escrito; A4 não executada**.
Fonte: tarefas_codex.md, rodada 3, T6. **Aguarda commit do autor antes de T7.**

## 1. Perguntas, alcance e reutilização

K2-A4: h-W melhora a previsão de remoção não programada registrada frente à
intensidade constante da coorte da frota? K2-idade: h-W melhora frente à h-E,
isolando a contribuição adicional da idade? A primeira resposta não basta para
fundamentar substituição preventiva por idade. Não são testes de economia de uma
política nem de falha física confirmada; esses limites de A5 permanecem.

Reutilizar a5_models.py e a5_validation.py: Exposure, training_view, incidência
concorrente, definição dos rótulos, métricas, agregação e bootstrap. Introduzir
somente um provedor de parâmetros hierárquicos e um adaptador de escala fixa.
Não copiar o mecanismo temporal de A5 para um segundo fluxo independente.
Refatorações compartilhadas exigem teste de equivalência dos resultados A5;
se alterarem resultados ou protocolo, registrar emenda antes de apresentar A4.

## 2. População, informação e partições

Mesmos 11 candidatos K1 de A5; apenas instalações observadas dentro de
01/01/2024–31/03/2026, removidas ou ainda em serviço. Mesmos IDs e chaves dos
trechos. K1 foi selecionado na janela completa; essa limitação é preservada.
Unidades anteriores não observadas e instalações posteriores à origem não
entram na população em risco. Não acrescentar P/N por terem bons resultados A4.

Origens mensais: 2025-01 a 2025-12, primeiro dia do mês. Corte: fim do dia
anterior. Horizontes: 1, 2 e 3 meses; intervalo [origem, origem + meses).
Treino expansivo desde 2024, recortando cada trecho e suas censuras na origem.
Nenhum instante, causa, exposição, hiperparâmetro ou diagnóstico futuro entra
no ajuste. Instalações são consideradas disponíveis na data registrada, com a
mesma limitação de ausência da data de inserção no sistema observada em A5.

Exposição principal: utilização diária da aeronave nos 90 dias anteriores,
aplicada aos dias do horizonte. Calendário: dias decorridos. Taxa observada
zero é zero; taxa sem informação não é convertida em exposição conhecida.
Idade de exposição nula não recebe epsilon; preservam-se exclusões por escala
e os casos na avaliação. Sem previsão hierárquica identificável, usar a base
constante (c), com motivo e cobertura explícitos, sem eliminar o alvo.

Remoções programadas/outras são riscos concorrentes. Sua intensidade por P/N
em unidades-dia é estimada no treino, com a mesma regra de fallback agrupado
de A5, e é idêntica para h-W, h-E e (c). Rótulos, integração da incidência,
censura administrativa e contagens por P/N × aeronave × horizonte são os de
A5_v1/emenda A5_001. Comparadores usam exatamente os mesmos casos de avaliação.

## 3. Escala fixada pelo domínio

| População | Escala principal | Sensibilidade específica |
|---|---|---|
| ATA 62, 64 e 32 | FH | Rodas ATA 32: decolagens |
| Coletes S-7200-* (ATA 25) | Calendário | Mantém calendário |

Não há seleção interna ou externa de escala pelos escores de A4. As escolhas
estão fixadas antes de rodar A4, depois de observar que a seleção de A5 escolhia
frequentemente escalas não identificáveis. Não atribuir a A5 uma aprovação
dessas escalas por mecanismo físico. T7 deve gravar um mapa P/N–ATA–família–escala,
verificando que cobre os 11 candidatos sem ambiguidades.

## 4. Modelos hierárquicos e estimação no treino

Famílias por mecanismo, cada uma com uma única unidade de exposição:
cabeças de rotor (ATA 62 e 64: tesouras, amortecedor, parafuso e terminal;
7 P/N; FH), rodas (ATA 32; 2 P/N; FH) e coletes (ATA 25; 2 P/N; calendário).
A tesoura do rotor de cauda entra com as do rotor principal por compartilhar
mecanismo de desgaste e escala; o agrupamento por ATA deixaria o ATA 64 com um
único P/N e sem encolhimento. Para P/N i da família f, h-W usa

    log(beta_i) ~ Normal(mu_beta,   tau_beta²)      nível global, 11 P/N
    log(eta_i)  ~ Normal(mu_eta_f,  tau_eta_f²)     nível por família

beta é adimensional e comparável entre escalas, por isso tem um nível global;
eta tem a unidade da escala da família e só é agrupado dentro dela.
Efeitos independentes condicionalmente aos hiperparâmetros; não estimar
correlação entre efeitos com tão poucos P/N. Ajustar hiperparâmetros pela máxima verossimilhança
marginal com aproximação de Laplace. A contribuição de cada P/N integra sua
verossimilhança de sobrevivência com censuras sobre os efeitos aleatórios.
Os modos condicionais entram nas previsões por unidade. A incerteza dos efeitos
não é substituída por pseudo-replicações; o bootstrap de aeronave avalia os
escores, sem alegar inferência Bayesiana completa dos parâmetros.

h-E restringe beta_i=1, tau_beta=0 e usa a MESMA estrutura normal para log eta,
famílias, elegibilidade, controles numéricos, procedimento marginal e orçamento
de otimização de h-W. Os hiperparâmetros de eta são reestimados no treino de
cada modelo; “mesmo encolhimento” significa mesma estrutura/procedimento e
possibilidade de regularização, não impor numericamente a variância ótima de
um modelo ao outro. Assim h-E pode obter sua melhor regularização sob a mesma
regra, sem favorecer h-W por um ajuste inadequado do comparador.

(c) é a intensidade constante de A5, na coorte dos candidatos, com denominador
em unidades-dia, não exposição da configuração completa instalada.

### Controle numérico e casos escassos

Somente scipy e numpy para estimação; pandas para leitura e organização já
existente. Otimização determinística: scipy.optimize, múltiplos pontos iniciais
fixos, sem seleção por validação externa. Hessiana da posterior condicional
positiva definida é necessária à aproximação de Laplace; registrar falha,
fronteira e número de tentativas. Não converter falha em bom ajuste.

Limites numéricos declarados: beta em [0,05; 20]; eta entre menor exposição
positiva/100 e maior exposição positiva × 100 no treino da família; tau_beta
entre 0 e 2 e tau_eta entre 0 e 3. Se houver modo na fronteira, sinalizar e
executar sensibilidade com limites ampliados (beta máximo 40, divisores/fatores
de eta 1 000, desvios máximos 4 e 6), sem substituir o principal pelo melhor.
Não usar resultados de A4 para escolher novos limites silenciosamente.

Inícios fixos: mu_beta em log(1) e log(2); mu_eta no ajuste agrupado do treino;
desvios iniciais 0,25 e 1, mais avaliações explícitas das fronteiras zero.
Por tentativa: até 2 000 iterações externas e 2 000 condicionais, tolerância
de objetivo 1e-8. Registrar orçamento e convergência por origem/família/modelo.
Variância zero reduz exatamente a dimensão, sem substituir zero por epsilon.

Com apenas um P/N no treino da família, fixar tau_eta_f em zero: não há
informação entre P/N para identificar a dispersão de eta; beta continua no
nível global. Com família inteira
sem cinco eventos válidos, usar (c), registrando insuficiência de informação.
Com família identificável, P/N com poucos ou zero eventos recebe encolhimento
usando também a exposição censurada disponível; não exigir cinco eventos por
P/N e assim reproduzir o problema que motivou A4. As famílias acima são
fixadas antes de executar A4; não reagrupar depois para melhorar um resultado.

## 5. Métricas, incerteza e dois critérios

Mesmas métricas de A5: log score Bernoulli (maior é melhor), Brier (menor é
melhor) e observado/esperado por decil de risco. Preservar probabilidades
originais; clipping a [1e-12, 1−1e-12] somente no logaritmo. Calibração e
fallback sempre relatados, inclusive se discordarem do critério principal.

Agregação principal: diferenças pareadas por unidade, média em aeronave/origem/
horizonte, depois médias de horizontes, origens e aeronaves com dados. Origem e
horizonte não são réplicas independentes. Bootstrap em blocos dos 24 códigos
de aeronave, 10 000 reamostragens PCG64, semente 20261112. Mesmos sorteios nas
duas comparações; grupos/P/N sem casos permanecem ausentes, não zero.

K2-A4 aplica a regra de K2 a h-W − (c). K2-idade aplica a MESMA regra a h-W − h-E:

- Favorável: limite inferior do IC agregado 95% percentil acima de zero.
- Mista: agregado não favorável, mas algum P/N com limite inferior simultâneo
  acima de zero, usando Bonferroni sobre os 11 P/N.
- Nula: demais casos.

As duas perguntas têm papéis distintos e ambas são relatadas. Não usar a melhor
das duas para declarar aprovação. A condição de prosseguir exige evidência
conjunta; não se busca significância selecionando uma delas.

## 6. Sensibilidades fixadas antes de executar A4

- **Agregação:** média simples das previsões unidade/origem/horizonte, mantendo
  o mesmo bootstrap por aeronave. Não implica independência de cada linha.
  A fragilidade do sinal em A5 já era conhecida; esta é sensibilidade pós-hoc
  declarada agora, não substituição da regra primária.
- FH realizadas no horizonte, identificadas como informação futura/programação
  conhecida, com integração diária de A5.
- Rodas em decolagens: casos completos e, separadamente, imputação pela razão
  decolagens/FH do treino. Não escolher escala por desempenho; preservar a
  população com fallback e informar a comparação restrita aos casos completos.
- Intervalos operacionais T2 reconstruídos no treino de cada origem.
- Proveniência da instalação, sob a regra de A5.
- Exclusão das quatro correções administrativas por chave completa, no treino
  e na avaliação, sem transformar o evento em censura independente.
- Limites numéricos ampliados quando houver fronteira, conforme seção 4.

Cada sensibilidade é isolada contra o principal e reestima seus hiperparâmetros
no treino. Nenhuma substitui os critérios principais por resultado favorável.

## 7. Interpretação pré-especificada e paradas

| K2-A4 | K2-idade | Interpretação e caminho posterior |
|---|---|---|
| Favorável | Favorável | Base preditiva e valor da idade sustentados; h-W pode fundamentar A7 após avaliação do autor |
| Favorável | Mista | Restringir futura A7 aos P/N com limite simultâneo positivo para idade |
| Mista | Favorável ou mista | Exigir interseção dos P/N sustentados simultaneamente nas duas comparações; sem interseção, parar |
| Favorável ou mista | Nula | Heterogeneidade pode ajudar previsão; idade não acrescentou evidência suficiente; parar, sem política preventiva por idade |
| Nula | Qualquer | Parar: a base preditiva exigida não foi demonstrada; se ambas nulas, seguir o caminho diagnóstico do plano |

Não generalizar o benefício da idade de um P/N para os demais. Mesmo com ambos
favoráveis, não houve ainda demonstração econômica ou causal de substituição.
T7 termina com atualização do plano e auditoria e comunicação ao autor,
**qualquer que seja o resultado**. Não executar A7 em T7.

## 8. Testes obrigatórios antes de executar T7

1. Dados simulados com 11 P/N heterogêneos: recuperar efeitos e hiperparâmetros,
   separando momentos dos onze efeitos realizados de hiperparâmetros populacionais.
   Usar fixture identificável com uma família e exposições suficientes; avaliar
   também configuração 7/2/2 para explicitar limites de dispersão com famílias
   pequenas. Semente 20261112; declarar tamanhos e tolerâncias antes do ajuste
   aos dados reais. Não prometer precisão populacional a partir de dois P/N.
2. Encolhimento com poucos eventos: em fixture controlada de eta conhecida,
   beta fica entre o ajuste individual e a média da família. No ajuste conjunto
   bidimensional essa propriedade não é universal; não truncar estimativas
   artificialmente para obrigar o teste. Registrar comportamento de ambos os efeitos.
3. Variância zero reproduz exatamente o ajuste agrupado. Limite de variância
   infinita refere-se ao modo condicional, cuja penalização desaparece e reproduz
   o ajuste individual identificável, não a uma integral marginal imprópria.
4. Evento futuro e voo posterior não alteram ajuste/hiperparâmetros passados.
5. Probabilidades válidas, monotonicidade, riscos concorrentes e conservação da
   população de avaliação; equivalência das rotinas reutilizadas com A5.
6. Determinismo em duas execuções completas, inclusive ajustes, bootstrap e decisões.

Os testes científicos h-W/h-E são requisitos de T7 e **não foram executados em
T6**, quando nenhum modelo A4 foi implementado ou ajustado. Testes do documento
verificam somente o contrato escrito, as fontes e a preservação de K2 de A5.

## 9. Artefatos e congelamento

Exportar mapa fixo de escalas, ajustes e hiperparâmetros por origem/família/P/N,
fronteiras/falhas, exposição/cobertura, predições individuais, contagens, métricas,
calibração, bootstrap pareado, decisões K2-A4/K2-idade e sensibilidades.
Manifesto com versões, sementes, hashes e revisão Git deste pré-registro.
Somente códigos anonimizados, números e hashes; nenhum texto livre operacional.

**Parar em T6 e pedir o commit deste arquivo ao autor.** O agente não faz commit.
Só depois executar T7 mediante autorização. Emendas posteriores ficam em arquivos
separados, com momento da decisão e conhecimento dos resultados; não reescrever
silenciosamente este protocolo. K2 nulo de A5 permanece no artigo e na auditoria.
