# Pré-registro A16/A9 — poder e condições de ganho

**Versão A16_A9_v1, 13/11/2026. Desenho feito depois de conhecidos A5 e A4.**
Alterações do autor antes do commit e de qualquer simulação: (i) o eixo de β
preserva a vida média de A4; (ii) as visitas seguem o calendário real de paradas;
(iii) orçamento total de T12 de 168 h de máquina (seção 5).
Este protocolo é pós-hoc em relação à evidência real, incluindo A15, e anterior
às simulações aqui propostas. Não reabre A5/A4 nem constitui validação externa.
Não houve holdout: todo o período disponível já foi visto. FH realizadas é
hipótese gerada pelos dados, incorporada como eixo de simulação, não confirmação.

**Estado: protocolo preparado; gerador, piloto, A16, A7, A9 e A10 não executados.
Parar para commit do autor antes de T12.** Alterações posteriores ao commit serão
emendas separadas, com momento, motivo e consequência inferencial. Este arquivo
não será alterado durante a execução. Não alterar paper/manuscript.tex.

## 1. Perguntas, estimandos e alcance

RQ3/A16: com verdade conhecida, qual a probabilidade de o protocolo de A4
detectar valor preditivo da idade? O estimando é a frequência de rejeição da
comparação h-W menos h-E, agregada e por P/N, condicional ao gerador e à seleção
fixa dos 11 P/N. Não repetir K1 para selecionar os casos sintéticos.

RQ4/A9: em que condições de β, conhecimento da utilização e deriva P2 economiza
recursos frente a P1? H2 restringe-se ao simulador. H3a testa equivalência
estacionária, H3b ganho após deriva; A4.1/A10 separa reestimação e otimização.
Nenhum resultado prova economia causal na frota real. Remoção registrada é o
desfecho; as intervenções assumem renovação perfeita de uma unidade sintética.
Inferência real usa aeronave; inferência entre simulações usa réplica pareada.

## 2. Entradas congeladas e rastreabilidade

- Aeronaves AC-01–AC-24, registros diários reais de FH/decolagens de
  data/anonymised/hours_flown.csv; janela jan/2024–mar/2026, encerrada no mesmo
  limite de observação de A4. Ausência de utilização não é imputada como voo.
- Datas de instalação e censuras de data/derived/spells.csv; mesma elegibilidade,
  exclusões, aproximações de inspeção e tratamento de entrada incompleta de A4.
  Usar somente campos estruturados anonimizados; não exportar texto operacional.
- Verdade Weibull: modos condicionais de h-W, variante principal, origem
  2025-12-01, data/derived/a4/effects.csv. Congelar β e η dos 11 P/N uma vez.
  Não usar um novo ajuste ou selecionar uma origem mais favorável.
- Escalas e famílias de config/a4_scale_map.csv: FH para rotor/rodas, calendário
  para coletes; manter os mecanismos 7/2/2 e o nível global de log β.
- Risco concorrente: competing_rate de individual_reference_fits.csv, principal,
  última origem, escala fixada e modelo w; registrar fallback original. Duplicatas
  equivalentes precisam concordar. Manter a unidade diária usada no código A4.
- Custos/MH: config/cost_parameters.csv, sem fabricar USD, dias ou recursos.
  Gerar manifesto com SHA256 de entradas, protocolos, código, versões, sementes,
  erros e exclusões. Saídas novas em data/derived/a16/ e a9/, nunca a4/ ou a5/.

## 3. Gerador comum e mecanismo de observação

Cada posição sintética tem aeronave, P/N, data inicial e relógio de idade própria.
Quando não houver identificador físico de posição, construir canais determinísticos
por coloração de intervalos de instalação observados (menor canal disponível,
ordem por data e chave estruturada estável). Isso é uma reconstrução sintética,
não identificação da posição real. Registrar canais, sobreposições e cobertura;
não inferir configuração certificada a partir deles.

Preservar as datas observadas de primeira instalação de cada canal. Instalações
posteriores registradas no mesmo canal serão marcos do desenho de observação,
não novas unidades adicionadas por cima de renovações simuladas: cada canal tem
uma unidade ativa, substituída por cada evento simulado. Registrar separadamente
a tabela completa das datas reais. Se a preservação literal de todas as instalações
impuser dupla ocupação ou reinício de idade sem remoção simulada, parar e apresentar
o conflito ao autor antes do piloto; não escolher silenciosamente outro desenho.

Idade operacional acumula FH/decolagens diárias reais e idade calendário acumula
dias. Gerar limiares independentes Exp(1) de risco acumulado por renovação,
H(a)=(a/η)^β. A remoção não programada ocorre quando o incremento de H cruza o
limiar. Gerar risco concorrente independente com a intensidade congelada de A4;
primeiro evento vence. Todo evento instala unidade nova na mesma posição e data.
Processar múltiplos eventos diários em frações do incremento, sem limite artificial
de um evento/dia. Empates numéricos: concorrente antes de não programado; visita
preventiva após os eventos daquele instante. Registrar incidência de empates.
Censurar no fim da janela e nos limites de observação aplicáveis a cada canal.

Registrar separadamente instalação real, estado latente, evento verdadeiro e
registro observável. Somente o último entra no ajuste. A aproximação de inspeções
de A4 será aplicada aos sintéticos, sem fornecer idade latente exata ao estimador
quando a observação real for intervalar. Proveniência e máscaras de relógio ausente
seguem A4. A seleção dos 11 P/N e seus mecanismos permanece fixa.

Nas derivas, integrar o risco com η(t), β e relógio vigentes, preservando idade e
risco acumulado; não sortear nova vida ao alterar η ou utilização. Reposição e
política são as únicas causas de renovação. Hipóteses: independência condicional
de unidades, riscos concorrentes independentes e utilização exógena às políticas;
não modelar falhas comuns, logística de sobressalentes ou realimentação de downtime
na produção de FH. Limites devem acompanhar as conclusões.

## 4. Validação do gerador: primeira barreira de T12

Antes de ajuste sintético ou comparação de políticas:

1. Testes de inversão do risco, renovação e censura com parâmetros conhecidos,
   incluindo β=1, relógios constantes/zero, entrada tardia e eventos concorrentes.
   Em amostra grande com relógio contínuo, estimativas/quantis devem concordar com
   os valores teóricos dentro de limites Monte Carlo pré-computados a 99%.
2. Gerar 1 000 réplicas do gerador calibrado (β e η de A4, taxas concorrentes
   congeladas). Medir remoções não programadas por exposição na escala
   fixada (FH ou dias), com o mesmo denominador e mecanismo observável dos dados.
   Taxa real por P/N deve estar no intervalo preditivo central simultâneo
   de nível 1−0,05/11 das 1 000 taxas simuladas. Reportar também razão média
   simulada/real e erro Monte Carlo; não substituir o teste por concordância agregada.
3. Comparar idades na remoção reais e simuladas por P/N: ECDF, quantis 10/50/90,
   censuras e intervalos reportados separadamente, usando o mesmo relógio e
   mecanismo observável. Reportar distância de Wasserstein normalizada pela
   mediana real quando definida. Não ajustar η ou β com essas discrepâncias.

**Parar e informar o autor se qualquer taxa por P/N falhar no gerador calibrado.**
Repetir a verificação de taxas nos níveis β=1 e ampliado, com η ajustado pela
regra de vida média da seção 5, e reportar as razões simulado/real; nesses níveis
a verificação é descritiva, porque a renovação depende da forma além da média.
Não recalibrar η com base nas discrepâncias. Não interpretar poder ou economia
antes desta barreira.

## 5. A16: desenho de poder e erro tipo I

Grade completa, sem seleção posterior:

| Eixo | Níveis |
|---|---|
| β verdadeiro por P/N | 1; modo de A4; 1+1,5×(modo−1) |
| Tamanho | frota real; ×2; ×4 |
| Exposição preditiva | principal: média móvel dos 90 dias; realized_fh: FH futuras conhecidas |

São nove células geradoras, avaliadas pelas duas variantes (18 combinações).
Replicar aeronaves com relógios iguais e processos de eventos independentes, IDs
sintéticos distintos e sementes diferentes. No bootstrap, cada cópia é um cluster
distinto; isso pressupõe cópias independentes condicionais aos relógios, não novos
operadores. Taxas concorrentes são iguais entre níveis. Em cada nível k, η é
ajustado para preservar a vida média de A4 por P/N:
η_k = η_A4 · Γ(1+1/β_A4) / Γ(1+1/β_k). Assim o eixo isola a dependência da idade,
sem alterar a taxa média de remoção. Regra fixada antes de qualquer simulação.

Aplicar o pipeline A4 sem alteração científica: treino por origem jan–dez/2025,
horizontes e elegibilidade de A4, mesmas verossimilhanças com censuras, limites,
Laplace, h-W/h-E/base, regularização e fallbacks. Reutilizar classes existentes
com caminhos de entrada/saída separados; não executar o main que escreve a4/.
Adaptação é apenas de entrada sintética, clusters replicados e B=999, explicitamente
autorizado. Nenhum hiperparâmetro é escolhido pelo desempenho no conjunto sintético.

Bootstrap B=999 por réplica, mesmo PCG64/20261112, com limites simultâneos
Bonferroni para os 11 P/N. A verificação real de T9 em
data/derived/a15/bootstrap_check.csv reproduziu decisões e subconjuntos de B=10 000
para principal e realized_fh, K2-A4 e K2-idade. Isso não garante precisão idêntica
nas caudas em todas as amostras simuladas; declarar essa limitação.

Rejeição agregada: limite inferior do IC 95% de h-W−h-E >0. Rejeição por P/N:
limite inferior simultâneo >0. Relatar separadamente classificação global
favorável/mista/nula de K2-idade e frequência de pelo menos um P/N retido.
Poder é taxa de rejeição sob β>1; β=1 estima erro tipo I agregado e familiar
(qualquer P/N). Sem tratamento favorável de convergências falhadas.

### Piloto, orçamento e número de réplicas

Após commit e aprovação do gerador, cinco réplicas de piloto, fora dos resultados,
medirão exclusivamente tempo e memória na célula ×4; executar ambas as variantes.
Não abrir tabelas de efeito/rejeição do piloto para escolher parâmetros.
Orçamento definido pelo autor: 168 h de máquina para T12, repartidas em
T_disponível = 48 h para A16 e 120 h para A9/A10, sem transferência posterior
de saldo entre estudos depois de abertos resultados.

Fixar R comum às nove células antes de abrir resultados principais:
R = 50×floor(T_disponível / (9×1,5×t_piloto) / 50), mínimo 200, máximo 1 000,
onde t_piloto é o maior tempo por réplica completa das cinco medições, ambas
as variantes incluídas; fator 1,5 reserva custo e variação. Limitar a 1 000 pelo
custo Monte Carlo já pequeno acima desse ponto. Se a fórmula resultar <200,
parar e apresentar custo estimado ao autor; não reduzir a grade ou R.
Registrar R, tempos e orçamento em manifesto assinado por hash antes da rodada.
Não aplicar parada opcional por significância ou resultados intermediários.

Intervalos binomiais de Wilson 95% para todas as frequências, erro Monte Carlo
sqrt(p(1−p)/R). Para R=200, erro máximo aproximadamente 0,035. Relatar réplicas
com falha na geração, ajuste e decisão; toda falha permanece no denominador
como não detecção e apresentar limites assumindo todas detectadas/nenhuma.
Se não for possível calcular o controle nulo em qualquer célula, parar a
interpretação correspondente; não classificá-la como erro tipo I zero.

### Interpretação fixada

- Se erro tipo I agregado ou familiar >0,10 em qualquer nível de tamanho/variante
  com β=1, parar e informar o autor antes de interpretar poder ou iniciar A9.
  Relatar Wilson e sensibilidade à precisão B=999, sem consertar a regra em silêncio.
- Poder agregado ≥0,8 nos modos A4/frota real: sob o gerador, o nulo observado
  sugere pequeno valor preditivo da idade nesses horizontes. Não é prova geral
  de ausência; o gerador foi estimado dos mesmos dados.
- Poder <0,5: nulo inconclusivo, reportar em qual tamanho se atinge 0,8, se houver.
- Poder entre 0,5 e 0,8: evidência fraca; reportar intervalos e gradiente por tamanho.
- Por P/N, aplicar as mesmas faixas à rejeição simultânea, sem substituir o
  agregado pela melhor peça. Variantes são reportadas juntas; principal governa
  a interpretação real. Casos com IC cruzando limiares recebem ressalva explícita.

## 6. A7 no simulador: políticas e custo

P0: somente corretiva (e risco concorrente exógeno comum).
P1: idade estática por P/N, calibrada no início com somente o histórico inicial,
aplicada na primeira visita elegível após o limiar. Reotimização proibida.
P2: h-W reestimado mensalmente com somente dados observáveis até a decisão;
MILP em horizonte rolante escolhe a visita preventiva com capacidade de MH.
P3: oráculo conhece parâmetros verdadeiros vigentes e o futuro caminho exógeno
de utilização do eixo conhecido, mas não limiares aleatórios de falha. Usa a
mesma ação factível e o mesmo horizonte. É referência superior de informação,
não limite determinístico para custo realizado nem oráculo clarividente de falhas.

Calibrar P1 por minimização da taxa esperada de custo de renovação no calendário
de visitas, usando parâmetros iniciais estimados, não a verdade do gerador.
Permitir limiar infinito (somente corretiva), inclusive quando β≤1. Calibrar
sem realizar tentativas sobre as réplicas de avaliação. Para evitar favorecer P2,
P1 e P2 partem do mesmo ajuste inicial e enfrentam as mesmas visitas/capacidades.

Custo adimensional: preventiva em visita=1; não programada fora de visita=r,
r∈{2,5,10}; não programada em visita=1. Visitas são instantes; em relógio diário,
fixar a convenção de coincidência antes de gerar eventos e manter em todas
as políticas. Riscos concorrentes exógenos têm custo unitário, igual entre
políticas, e são reportados separadamente para tornar sua contribuição visível.
Custos de P0–P3 incluem todas as substituições, sem duplicar penalidade/downtime.
USD só se os parâmetros hoje AUTOR_DEFINIR forem preenchidos pelo autor.

Usar MH preventiva central por P/N de documentos de remoção única de T4 como
demanda de capacidade, sem tratá-la como medida causal de preventiva. Falta de
MH não vira zero: parar a instanciação desse P/N e informar o autor. Relatar
essa aproximação e sensibilidade usando faixas empíricas disponíveis.

### Visitas, horizonte e instância operacional

Horizonte de avaliação: 24 meses jan/2024–dez/2025 de relógios reais; aquecimento
e ajuste inicial usam histórico sintético de 12 meses anterior, com o primeiro
ano de relógios repetido e sementes independentes, sem misturar eventos reais.
Deriva no início do mês 13, após 12 meses completos; janela pós-deriva de 12 meses.
Os rótulos de mês 12 da tarefa designam esse ponto de mudança t=12 meses.
Essa extensão é simulada, não dado novo. Canais e entradas usam o mesmo mecanismo
da seção 3; se instalações tardias impossibilitarem aquecimento de uma posição,
manter a entrada tardia e reportar o caso, sem fabricar idade histórica.

Visitas exógenas por aeronave: datas de início das paradas reais de
data/derived/stoppages.csv (manutenção progressiva, mediana de ~7 dias ou ~18 FH
entre paradas), respeitando as datas de entrada dos canais. No aquecimento de
12 meses, repetir o calendário de paradas do primeiro ano de cada aeronave.
Na deriva B-util, manter as datas reais das paradas (utilização exógena).
Capacidade por visita = soma de MH dos P/N ativos nessa aeronave dividida por 4;
mesmo orçamento por política; não escolher a capacidade que maximize ganho.
Sensibilidade A11: metade e dobro desse orçamento; calendário mensal no primeiro
dia útil, somente no simulador, para medir o valor da densidade de oportunidades.
Corretivas emergenciais não disputam capacidade preventiva, mas seu MH é reportado.

Horizonte MILP: resolvido a cada atualização mensal, com todas as visitas dos
6 meses seguintes, executando as decisões das visitas até a próxima atualização; ao fim do período de avaliação, simular extensão de relógios repetidos
para avaliar custo terminal, sem incluir esses eventos no desfecho principal.
Mesma extensão/horizonte para todas as políticas e referência estática. Fixar
o custo terminal como custo esperado até completar o ciclo de renovação em
curso; testar consistência em instâncias estacionárias antes de comparar políticas.

### Contrato matemático do MILP

Para unidade u e visita j: x[u,j]∈{0,1}, incluindo opção não substituir dentro
do horizonte. Colunas representam sequências admissíveis de renovação preventiva
por unidade, com custos esperados de corretivas/concorrentes e preventivas sob
o modelo congelado na decisão. Selecionar exatamente uma sequência por unidade;
capacidade por visita: soma de MH[u]×incidência[u,j]×x[u,sequência] ≤ capacidade[j].
Incluir sequência sem preventiva e múltiplas preventivas quando admissíveis.
Custos de sequências são calculados por integração da renovação no relógio
diário e riscos concorrentes; não usar probabilidade marginal somada como se
não houvesse renovação. Registrar erro de quadratura e verificar com casos
analíticos/enumeração. Sem folgas de capacidade que produzam solução inviável.

CBC via python-mip, uma thread, semente fixa, gap relativo 1e-6, limite 300 s
por decisão. Registrar status, bound, gap e runtime. Ótimo não provado não será
rotulado ótimo. Fallback determinístico: manter plano anterior se factível,
senão nenhuma preventiva; nunca omitir a política/réplica do custo acumulado.
Testes pequenos devem atingir ótimo comprovado; falhas bloqueiam a execução.

## 7. A9/A10: grade, inferência e paradas

β: 1, modos A4 e 1+1,5×(modo−1). Conhecimento de utilização: prevista pelos
90 dias passados ou conhecida no horizonte, compartilhado por P1/P2; P1 mantém
limiar fixo, só localiza sua próxima visita. r: 2,5,10. Tamanho: frota real.

| Cenário | Verdade do gerador |
|---|---|
| A | Parâmetros e regime de utilização estacionários |
| B-eta | A partir de t=12 meses, η do rotor cai 30% |
| B-util | A partir de t=12 meses, incrementos de utilização sobem 30% |
| B-gradual | η do rotor cai linearmente até −30% entre t=12 e t=24 meses |

A preserva os relógios reais, que variam diariamente; estacionário significa
ausência de mudança imposta, não utilização constante. Reportar essa variação.
No B-util multiplicar FH e decolagens por 1,3 (relógio operacional contínuo),
sem arredondar decolagens ou alterar calendário dos coletes. Nas outras derivas,
alterar somente η do rotor. Nunca reunir as três derivas numa estimativa única.
Total: 3×2×3×4=72 células, reportando P0–P3 e as duas ablações de P2 em cada uma.

R=200 por célula como mínimo, comum a políticas; orçamento da execução A9 será
medido em piloto de cinco réplicas excluídas. Aplicar a regra da seção 5, trocando
nove por 72; se o mínimo não couber, parar para decisão do autor, sem reduzir
escopo. SeedSequence(20261112), separando fluxos por estudo, célula, réplica,
aeronave/cópia, canal, tipo de evento e renovação. Não usar hash() de Python.
Mesmos limiares de risco e relógios por réplica nas políticas (common random
numbers), com indexação por renovação/tipo; ações diferentes podem consumir
números diferentes, mas não alterar o fluxo de outros componentes.

Desfechos: custo total adimensional, preventiva/não programada, eventos fora
de visita e MH, por réplica e política. Downtime real não é identificado;
reportar apenas proxy se coeficientes forem fornecidos, separadamente.
Δ = (C_P1−C_P2)/C_P1, positivo favorece dinâmica, denominador por réplica;
se C_P1=0, reportar diferença absoluta e caso indefinido, sem remover réplicas
do teste absoluto. Reportar também razão das médias com IC pareado.

H3a: TOST a 5%, IC t pareado 90% para média de Δ inteiramente em [−0,02;0,02].
Ausência de significância não implica equivalência. H3b: média de Δ nos 12 meses
pós-deriva com IC t pareado 95% inteiramente acima de zero. Inferência por
célula, sem alegação global decorrente da melhor célula; disponibilizar valores-p
e ajuste Holm entre as 54 células B para uma alegação familiar de ganho.
Relatar magnitude, dispersão e negativos, inclusive β=1. Se pressupostos do IC t
forem inadequados, reportar bootstrap pareado B=10 000 como sensibilidade,
sem trocar a decisão primária retrospectivamente.

Detecção: primeira atualização mensal com IC Wald 95% de log η do rotor
inteiramente abaixo do IC do ajuste inicial, por P/N; declarar definição
operacional e múltiplos alarmes. Reportar taxa de alarmes em A, tempo ao primeiro
alarme em B e censura em 12 meses. B-util também mede primeira previsão de
utilização ≥1,15×média inicial por dois meses seguidos; distinguir detecção de
exposição de detecção de parâmetro. Não usar o verdadeiro instante na política.

A10: P2 sem reestimação, mantendo parâmetros iniciais e otimizando visitas;
P2 com reestimação mas regra de idade P1 recalibrada mensalmente, sem MILP.
Mesmos custos, capacidades e informações. Se limiar gerar conflito de capacidade,
priorizar maior custo esperado evitado por MH, desempate P/N e canal.

**Paradas e interpretação:** ganho de P2 além de 2% em A com IC 95% inferior
>0,02 sugere viés e exige parada/revisão antes de alegar adaptação. Falta de
equivalência isolada é inconclusiva, não prova de viés. Ausência de ganho em B
com β>1 indica que o ciclo não reage sob essa condição; registrar sem trocar
cenário ou política. P3 pode perder em uma realização; vantagem sistemática de
P2 sobre P3 exige auditoria da referência, sem prometer limite de custo amostral.
O produto é o mapa completo de condições e a posição dos modos β da frota e
da utilização prevista nesse mapa, com incerteza e sem economia real atribuída.

## 8. Testes e entrega

Antes da execução principal: recuperação de parâmetros conhecidos; erro tipo I;
limites de idade, entrada, censura e riscos; uso somente de passado; capacidade
e índices por unidade/visita; MILP versus enumeração manual em instâncias de
duas unidades/três visitas; renovação repetida; custo terminal; pareamento
de sementes; determinismo em duas execuções pequenas completas.

Salvar configuração congelada, tempos do piloto, R e sementes antes dos resultados;
depois, resultados por réplica, parâmetros estimados, previsões, falhas/fallbacks,
status CBC, intervalos e mapas. Artefatos anônimos, sem texto livre operacional.
Comparar hashes dos artefatos A5/A4 e dos pré-registros antes e depois de T12.
Não sobrescrever resultados históricos ou reduzir falhas à categoria nulo.

T12 executa validação do gerador → A16 → barreira de erro tipo I → A9/A10.
Informar o autor nas paradas de taxas, erro tipo I e controle estacionário e ao
final. Atualizar plano e auditoria; emendas em arquivos separados.

**Parada atual obrigatória: solicitar commit deste pré-registro ao autor.
Nenhum piloto ou experimento desta seção está autorizado antes desse commit.**
