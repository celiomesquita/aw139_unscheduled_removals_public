# Emenda A16/A9_014 — proposta de superfície de calibração de idade

15/11/2026. **Proposta preparada; não implementada nem executada.** Posterior
à interrupção expressamente autorizada do PID 34396 e à entrega da
[decomposição computacional](a9_partial_time_decomposition.md), anterior a
qualquer construção/validação de superfície. Nenhum custo realizado, ganho,
contraste ou alarme da avaliação foi aberto. A réplica parcial não entra em R.
Os pré-registros e as emendas executadas permanecem intactos.

## 1. Objeto e mudança científica explícita

Substituir a busca exaustiva repetida da calibração de idade por consulta a uma
superfície pré-computada do limiar, usando o método exato vigente nos nós.
Aplicar à calibração inicial de P1 e à recalibração mensal de P2_age; alterar
somente P1 deixaria as 23 recalibrações de P2_age como gargalo.

O executor atual minimiza a soma ponderada das taxas de renovação para obter
**um limiar por P/N, comum às aeronaves**. A superfície solicitada fornece
**um limiar por P/N e aeronave**. Esta é uma mudança da classe de políticas
de referência, além de uma aproximação numérica. Não pode ser certificada como
equivalência das emendas 012/013. P1 continua estática após o ajuste inicial;
P2_age continua mensal. O contraste P2–P1 passa a usar essa referência mais
flexível; o erro de interpolação será validado contra o ótimo exato individual,
não contra o antigo ótimo ponderado comum. Não alegar identidade dos ganhos.

Preservar as seis políticas, as 72 células, r={2,5,10}, R mínimo 200,
24 meses, capacidades, MH, gerador, deriva, sementes e números aleatórios
comuns. Preservar a observabilidade, entradas tardias e o ajuste A4. A capacidade
continua tratada pela regra de seleção factível já vigente: a superfície otimiza
a taxa de um contexto isolado e não resolve conjuntamente a capacidade.

Permanecem as limitações da emenda 010: idade zero no primeiro marcador
observado, truncamento à esquerda das idades reais; o ano auxiliar estacionário
permanece em todos os ajustes, inclusive nos cenários B. Não regenerar a coorte
auxiliar já materializada nem continuá-la na avaliação.

## 2. Índices, domínios e nós fixados antes de qualquer validação

Uma tabela é indexada por (P/N, aeronave, escala, r, hash do calendário de
visitas, hash do relógio diário inicial). Dentro dela:

`a*(β, η, ν; calendário, relógio, r)`, com ν por dia de calendário.

O peso de um contexto isolado multiplica a taxa e não altera seu argmin.
Compartilhar nós somente quando calendário, relógio, escala, r e tolerâncias
forem idênticos. A identificação P/N/aeronave permanece no manifesto. Não
compartilhar idade corrente nem informação de resultados. Calendários iniciais
ficam congelados também nas consultas mensais de P2_age; não usar visitas futuras
da avaliação para atualizar a tabela. Ausência de contexto histórico mantém o
ramo vigente sem prevenção; não fabricar um calendário para entradas tardias.

Seja E a exposição total do ciclo inicial de 365 dias do contexto: FH ou
365 dias conforme a escala. Os eixos da proposta são:

- β: **[1.001, 1.01, 1.05, 1.1, 1.25, 1.5, 2, 3, 4, 6, 8, 12]**;
- η/E: **[1/64, 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2, 4, 8, 16, 32]**;
- 365ν: **[0, 0.001, 0.01, 0.03, 0.1, 0.3, 1, 3, 10]**.

São 1 296 nós por contexto único e r. Esses limites são escolhas numéricas
de cobertura, não intervalos de confiança nem garantias de conter os ajustes.
β≤1 mantém analiticamente o limiar infinito. β>1 fora da caixa, η/E fora da
caixa, ν fora da caixa ou parâmetros inválidos não são truncados para caber.
Acionam o método exato, com registro de ocorrência e tempo, ou falha explícita
se não houver recurso. O custo desses fallbacks integra o piloto e o ledger.
Não expandir a caixa ou mudar nós após validar: qualquer alteração exige nova
versão, registro e conjunto de validação independente antes de avaliar políticas.

Nos nós, chamar o método exato atual `calibrate_threshold` de
a9_static_fast.py, com **um contexto**, grades de fases 1/2/4 e critério
vigente 1e-4+1e-3|taxa|, massa/caudas e refinamento das emendas 011/013.
Não confundir esta grade de parâmetros com redução da grade temporal científica.
Persistir limiar, taxa esperada, ramo infinito, todas as contagens de breakpoints,
grades usadas, tempos, memória e hashes. Nó sem convergência não vira dado
interpolável. A presença de um nó falho impede liberar sua célula.

## 3. Interpolação e fronteiras

Usar interpolação trilinear em (log β, log(η/E), log1p(365ν)), com valor
log1p(a*/E) quando os oito vértices são finitos. Retornar o limiar na escala
original, sem arredondar a visita ou antecipar uma decisão. A regra vigente
de primeira visita elegível e o desempate de capacidade continuam separados.

Não interpolar infinito como número. Se os oito vértices forem infinitos,
o candidato é infinito. Em célula mista finito/infinito, consultar o método
exato. A amostra de validação inclui células só infinitas: oito vértices
infinitos não provam ausência de ótimo finito no interior. Descontinuidades
do argmin podem invalidar interpolação mesmo entre limiares finitos. A regra
de tolerância abaixo, e não a suavidade presumida, governa a liberação.

## 4. Validação fixada antes de construir a superfície

Semente independente **20261115014**, exclusivamente para planejamento da
validação, sem reutilizar os fluxos de aquecimento/avaliação. Ordenar templates
pelo SHA-256 e r em [2,5,10]. Para cada par template/r, gerar **300 pontos
independentes**, uniformes na caixa transformada acima, por
`SeedSequence([20261115014, template_index, r_index])`, e acrescentar os **26
pontos de fronteira** obtidos de mínimo/meio/máximo de cada eixo transformado,
exceto o centro. Salvar pontos e hashes antes de computar qualquer resposta.
Acrescentar testes analíticos de β≤1 e testes de roteamento fora da caixa;
esses testes não substituem os 326 pontos numéricos de cada template/r.

Em cada ponto, calcular o ótimo exato com um contexto e a taxa exata do limiar
interpolado, na mesma discretização convergente. Não executar uma trajetória
de avaliação. Definir arrependimento numérico

`regret = J(limiar_interpolado) − J(limiar_exato)`.

Aceitar somente se **todos** os pontos satisfizerem

`abs(regret) ≤ 1e-6/365 + 1e-3 * abs(J(limiar_exato))`

e as verificações vigentes de massa, cauda, positividade e estacionariedade.
O módulo também detecta possível inconsistência do avaliador exato. Usar taxa
de custo total do contexto, inclusive termos constantes, com as mesmas unidades.
O piso absoluto é 1e-6 por ciclo de 365 dias; a parcela relativa é 0,1%.
Reportar separadamente erro relativo quando a taxa ótima for positiva,
deslocamento do limiar, divergência de ramo finito/infinito, fallbacks e
convergência. Não exigir proximidade de limiares se a taxa for equivalente,
pois o argmin pode mudar abruptamente. Divergência de ramo só passa se a mesma
tolerância de taxa for satisfeita. Não ajustar tolerância após ver os erros.

Essa tolerância é adicional, não relaxamento do método nodal. Se sua precisão
não permitir decidir, falhar a validação: não aumentar tolerância nem refinar
a grade científica silenciosamente. A amostra valida erro numérico amostral;
não fornece garantia uniforme no domínio nem garante erro inferior a 0,1%
no custo realizado de uma política sujeita a capacidade. Não transformar
arrependimento de taxa estacionária em garantia para o contraste H3a de 2%.

Qualquer falha bloqueia a superfície inteira nesta versão. Manter a falha e
apresentar revisão em nova emenda; não selecionar células ou pontos favoráveis.
Versões revistas usam nova semente declarada antes e não reutilizam esta
amostra como validação independente. Não abrir desfechos para decidir refinamento.

## 5. Estimativa computacional e orçamento

O [ledger atualizado](../data/derived/a9/decomposition/accumulated_costs.json)
preserva o anterior: **89 780,234678 s conhecidos**, incluindo **86 954,802319 s**
deste piloto interrompido. Sobram **no máximo 342 219,765322 s = 95,061046 h**.
Lacunas de medições anteriores permanecem; disponibilidade é limite superior.

Para R=200, 72 células e reserva 1,5:

`B_construção + B_validação + B_testes + B_novo_piloto + 21 600 * t_max ≤ 342 219,765322 s`.

t_max é o maior dos cinco tempos completos válidos do novo piloto, incluindo
geração/carga do aquecimento conforme o caminho executado, ajustes, todas as
políticas, consultas, MILPs, escrita, fallbacks e monitoramento. O tempo de
construção e validação é pago uma vez, dentro das mesmas 120 h. R permanece
indefinido até cinco medições válidas; não iniciar piloto sem perspectiva
de cumprir orçamento. Nenhuma execução desta proposta está autorizada por
seu simples registro.

O inventário computacional da coorte auxiliar já existente tem **129 pares
P/N–aeronave informativos**, **38 templates distintos** por relógio/calendário.
Ele não é uma garantia de cobertura dos contextos presentes em futuras coortes.
O manifesto completo deverá cobrir a união dos contextos iniciais permitidos
pelo desenho antes da construção; templates adicionais aumentam o custo.
Fonte: ../data/derived/a9/decomposition/surface_planning_inventory.json.
Com somente esses 38 templates, a proposta já requer **147 744 calibrações exatas
nodais e 37 164 pontos exatos de validação**, além de avaliar as taxas dos
limiares interpolados. Total mínimo do inventário: **184 908 calibrações**.

Tabela de sensibilidade de planejamento, **não benchmark medido**: seis
trabalhadores com utilização perfeita, sem custos adicionais, mesmo tempo médio
q para nó/validação. Concorrência real será limitada também pela memória.

| q por calibração exata | Construção + validação, ideal | Máximo permitido por réplica, após esse gasto |
|---:|---:|---:|
| 1 s | 8,5606 h | 14,4167 s |
| 5 s | 42,8028 h | 8,7097 s |
| 10 s | 85,6056 h | 1,5759 s |
| 60 s | 513,6333 h | orçamento excedido antes da avaliação |

Os três primeiros números da última coluna também ignoram testes, novo piloto,
avaliação de taxas e fallbacks. São cenários otimistas, não previsões de duração.
A média nodal teria de ser **<11,1045 s** com seis trabalhadores perfeitos até
para construir/validar antes de esgotar o saldo, ainda sem executar avaliação.

Conferência posterior à entrega: duas reconstruções idênticas, seis testes
pertinentes aprovados, 8 077 artefatos históricos e fontes/insumos congelados
intactos. Seus **41,674101 s** foram debitados no
[ledger após verificação](../data/derived/a9/decomposition/accumulated_costs_after_verification.json),
sem reescrever o snapshot da interrupção: acumulado **89 821,908778 s**,
saldo **≤95,049470 h**, teto por réplica sem novos gastos **15,8416 s**.
Os cenários acima usam o snapshot anterior e são limites ainda mais otimistas;
na fórmula, essa conferência já debitada não deve ser contada novamente em B_testes.

Quanto ao tempo por réplica com consulta: a parte de calibração deixa de ter
busca exaustiva em cada origem, mas o novo tempo completo **não é identificável
pelos registros existentes**. Modelo de estimativa:

`t_novo = t_aquecimento/ajuste + soma(t_seis_políticas_sem_calibração) + t_consultas + t_fallbacks`.

A telemetria só limita as calibrações já executadas a ≥74 830 s e o restante
da réplica parcial a ≤12 124,802319 s. Esse restante mistura o excesso acima
dos limites de calibração com ajustes/MILPs/simulação e exclui os 18 meses
de P2_age não iniciados. Não é uma medição de t_seis_políticas_sem_calibração.
Logo não autoriza um ETA pontual ou extrapolação de speedup. Mesmo supondo
construção gratuita e zero fallbacks, **t_novo precisa ser ≤15,8416 s**; não há
evidência de que todas as demais operações satisfaçam esse limite.

**Conclusão de viabilidade: R=200 em 120 h não está demonstrado para a mudança
proposta; a versão exata anterior permanece inviável. Não afirmar que a
superfície cabe, nem afirmar impossibilidade matemática da nova versão com
base em tempos não medidos. Execução parada, sem construir a superfície,
retomar a réplica 0 ou escolher R.**

## 6. Opções que preservam grade, R e políticas

1. Autorizar uma etapa curta de perfilamento sem desfechos, com teto de tempo
   previamente debitado, persistindo relógios/RSS/contagens a cada etapa e job.
   Medir custo exato por template/nó e ajustes/MILPs em entradas artificiais
   representativas; esses microbenchmarks não substituem as cinco medições
   completas requeridas para R. Só construir após uma projeção explícita caber.
2. Ampliar orçamento e/ou usar infraestrutura computacional adicional. Medir
   throughput e limites de RAM; preservar sementes, calibração e ledger.
   Não declarar horas de CPU paralelas como equivalentes a horas de parede
   sem definir a convenção de orçamento antes da execução.
3. Investigar redução algébrica adicional do método exato, reuso de contextos
   idênticos e paralelização entre réplicas, incluindo ajustes e MILPs, mantendo
   todos os nós, políticas, grade e precisão. Exigir equivalência e novo perfil
   antes de prometer viabilidade. Não deduzir aceleração do benchmark de kernels.

Nenhuma opção reduz o desenho principal ou desloca silenciosamente o custo
offline para fora das 120 h. O estado vigente é proposta pendente, sem nova
execução científica.
