# Emenda A16/A9_015 — proposta: referência Linux, R fixo e calibração por idade

17/11/2026. **PROPOSTA para auditoria, autorização e commit do autor.**
T17 encerrada pela decisão do autor e pela comparação completa da errata A4.
A calibração aqui proposta, sua verificação, T20 e a execução principal A9/A10
**não foram implementadas nem executadas nesta rodada**. Nenhum ganho, contraste
ou alarme A9/A10 foi aberto para escolher este método ou seus controles.
Os pré-registros e resultados históricos permanecem intactos.

## 1. Decisões já vigentes e escopo prospectivo

A decisão vigente do autor de 17/11 fixa **336 h (14 dias corridos) de parede
nesta máquina**, para tudo o que resta da A9/A10: preparação e cálculo das
referências exatas, verificação da calibração, T20, ensaio técnico, execução
principal e verificação final. O relógio começa no **commit desta emenda 015
revisada, feito pelo autor**. A revisão documental não inicia esse relógio.

A grade completa continua como alvo e é a única execução principal autorizada:
**72 células, seis políticas e R = 200 por célula**, ou 14.400 réplicas pareadas
e 86.400 trajetórias de políticas. Não há seleção de R por tempo ou resultado,
nem redução automática de células, políticas ou R.

O critério de escopo fica fixado **antes da T20**: se o tempo restante
projetado, com reserva de 1,5, exceder **336 h menos o tempo já consumido**,
parar a execução principal e adotar a RQ4 como **protocolo mais piloto de
viabilidade**, deixando a avaliação completa como trabalho futuro. Não se
substitui a grade por uma subgrade. No artigo, distinguir RQ1–RQ3 concluídas
da RQ4 não respondida, ajustar objetivo e contribuições e não afirmar ganhos
econômicos ou prescritivos não demonstrados. A seção 7 define a contabilidade
sem duplicar consumo.

Esta proposta substitui somente a calibração de idade de **P1**, uma vez no
início, e de **P2_age**, a cada origem mensal. Mantém um **limiar comum por P/N**,
as escalas fixadas, o ramo infinito para beta <= 1, a primeira visita elegível
e a mesma regra de capacidade/priorização factível. Preservar P0, P2, P3,
P2_fixed e os demais cálculos de P2_age, custos, MH, visitas, deriva, utilização,
observabilidade, sementes e pareamento. Coeficientes monetários continuam
`AUTOR_DEFINIR`; custo preventivo 1 e corretivo r são adimensionais, com
r em {2, 5, 10}, como no protocolo.

A superfície da proposta 014 permanece rejeitada, sem execução. Não se adota
limiar individual por aeronave nem se reduz a grade experimental.

## 2. Troca definitiva de máquina e encerramento T17: desvios declarados

Os experimentos restantes usam Linux, Intel i7-9700F, oito núcleos lógicos,
aproximadamente 31 GiB de RAM, `.venv/bin/python` 3.14.0 e as versões do lock:
numpy 2.4.0, scipy 1.17.1, pandas 2.3.3, mip 2.0.2, cbcbox 2.937. A origem era
Windows 11, 22 processadores lógicos e 63,5 GiB. Sistema, CPU e binários das
bibliotecas matemáticas mudaram apesar da coincidência das versões Python.
Essa troca é um desvio de ambiente, não uma nova amostra científica.

A tentativa Python 3.12 ficou preservada e foi substituída antes da validação
final. `config/confidential/` continua ausente; não foi recriado nem necessário
às análises anônimas executadas. Nenhum arquivo confidencial foi copiado.

O histórico abaixo foi escrito **depois de observar diferenças**. Não deve
ser apresentado como critério de reprodução pré-registrado antes delas:

| Etapa | Regra/observação e consequência |
|---|---|
| T17b | Tolerância absoluta 1e-12 entre máquinas; A15 diferia por ulp |
| T17c | atol=1e-8, rtol=1e-6 para a reprodução A5, motivados pela precisão do Nelder–Mead; A16 expôs precisão distinta do ajuste hierárquico |
| T17d | Decisões/sinais exatos, teto científico 1e-4 e diagnósticos contínuos relatados; houve divergência em successful_attempts |
| T17e | successful_attempts passou a diagnóstico; surgiu excesso de delta_log por P/N em provenance |
| T17f | Agregado absoluto, limites por P/N relativos à margem; zero_variance mudou na principal |
| Encerramento do autor | Só bloqueiam decisão diferente, sinal de limite diferente e falta de identidade byte a byte local. Todo o restante é relatado, sem bloquear |

A comparação final cobriu oito variantes A4, 30/60 dias e B=10.000. Duas
execuções completas produziram **176 CSVs científicos idênticos byte a byte**.
Desfechos, conjuntos Bonferroni por P/N e sinais dos limites foram iguais aos
históricos. A16 e decomposição também têm provas locais de identidade já
preservadas. A suíte final passou com **201 testes**.

Na principal, agregado por aeronave, para ambos os limiares de exposição:

| Critério | Campos | Histórico | Linux | Módulo do deslocamento / margem histórica |
|---|---|---:|---:|---:|
| K2-A4 | ci_lo e simultaneous_lo | 0,00015577995223528334 | 0,00015493323275380332 | 0,005435355893556651 (0,5435%) |
| K2-idade | ci_lo e simultaneous_lo | 0,0007890227994342046 | 0,0007885739887758877 | 0,0005688183644867947 (0,05688%) |

Os limites permaneceram positivos. Isso confirma a transferência das decisões,
não uma confirmação científica independente da errata A4. A5 nula permanece
preservada; a errata não substitui os resultados originais.

**Referência de reprodutibilidade daqui em diante:**
`data/derived/machine_transfer/linux_reference_manifest.json` e seu arquivo
`linux_reference_20261117.tar.gz`. Os resultados Windows ficam intactos em
seus caminhos históricos. O novo padrão numérico não retuna automaticamente
os parâmetros verdadeiros congelados do gerador, nem altera coortes, sementes
ou hipóteses dos protocolos já executados.

## 3. T18: processos, CPU, parede, memória e orçamento de 336 h

Declarar antes de medir: **seis trabalhadores + um coordenador + um processo
de recursos**, até oito processos Python. Usar `spawn`, um thread por processo
para BLAS/OpenMP/NumExpr e um thread do CBC. Substituir o lançador pelo Python
com `exec`. O limite de processos é do executor; serviços do sistema não são
contados como trabalhadores. Não executar réplicas pareadas concorrentes nessa
configuração: o paralelismo é interno à réplica e já entra em seu tempo medido.

Tempo de parede usa relógio monotônico do início ao fim de cada operação,
incluindo carga, geração auxiliar quando necessária, ajuste, calibração,
espera, MILP, simulação e escrita. CPU é user+system por processo, registrada
separadamente; agregar PIDs distintos sem contar filhos novamente no pai.
**Nunca somar CPU ao ledger de parede nem dividir o tempo já paralelo pelo
número de processos.** Intervalos paralelos não são somados como se fossem
sequenciais; a operação completa é debitada uma vez por sua duração de parede.

Congelar antes da execução a alocação de memória em **70% da RAM disponível**,
com valor em bytes e instante registrados. Admitir tarefas pelo estimador de
memória e registrar RSS agregado e por processo. Pode-se serializar tarefas
pela regra de admissão declarada; não reduzir fases, quadratura, grade,
políticas ou R para caber. Falta de memória é um impedimento técnico a informar,
não justificativa para mudar precisão ou escopo.

O registro de encerramento
`data/derived/machine_transfer/closure_time_ledger.json` é um retrato histórico
da decisão anterior, sem teto; não será reescrito para simular a decisão nova.
A execução revisada terá um ledger prospectivo separado, em
`data/derived/a9/amendment015/time_ledger.json`, com o commit inicial, instante
UTC de início, prazo final, consumo global e saldo das **336 h**. O relógio
corrido não reinicia em interrupções ou retomadas. O consumo inclui todas as
etapas restantes, também referências exatas e tentativas malsucedidas.
O consumo global é o intervalo corrido desde o commit; as durações das
etapas são sua decomposição diagnóstica, não valores a acrescentar de novo
a esse intervalo. Persistir os instantes necessários para retomar o relógio
sem descontar pausas nem reiniciar a contagem.

Preservar as fontes e lacunas históricas, sem converter durações Windows para
equivalentes Linux e sem imputar zero onde não houve medição. Os tempos
anteriores ao commit revisado permanecem no histórico, mas **não são debitados
outra vez das novas 336 h**. Até o fechamento da T17:

| Registro | Quantidade conhecida | Natureza |
|---|---:|---|
| Ledger histórico A9/A10 | 89.821,90877819996 s = 24,950530 h | Parede registrada, com lacunas históricas explícitas |
| Segmentos medidos de transferência T17 | aproximadamente 0,665633 h | Parede de suítes/verificadores Linux; não inclui preparação sem relógio |
| A16 histórico | 127.973,59695030047 s = 35,548221 h | Soma de durações de trabalhadores; **não** tempo de parede, não somada às linhas anteriores |

Os 60 h/120 h das emendas anteriores e seus saldos ficam somente como histórico.
Os segmentos T17 incluem tentativas malsucedidas; durações de trabalhadores
internos não são contadas outra vez. A execução interrompida em Python 3.12
e preparação/arquivamento sem relógio continuam lacunas, não custos zero.
O total acima não é uma estimativa do custo completo de todo o projeto.

### Histórico das decisões de orçamento e regra vigente

| Sequência | Decisão do autor e efeito |
|---|---|
| Emendas anteriores | Tetos históricos de 60 h/120 h, preservados como registro das execuções da época |
| 17/11, sem limite | Retirada do teto; R=200 fixado e ledger apenas descritivo, como na versão anterior da proposta 015 |
| 17/11, duas semanas | Decisão que substitui a anterior: 336 h de parede para toda a A9/A10 restante, a partir do commit da emenda revisada |
| 17/11, critério de escopo e referências | Antes da T20, fixado o desfecho protocolo mais piloto se a grade não couber; cálculo das referências autorizado com subteto global de 24 h dentro das 336 h |

Essa sequência é relatada como mudança de decisão e desvio, sem apagar o
histórico nem aplicar retroativamente o teto novo aos tempos já gastos.
Medições futuras servem ao calendário, ao saldo e ao critério de escopo
pré-fixado. **R permanece 200**: nenhum piloto, perfilamento, fórmula antiga
de orçamento ou resultado o modifica. O subteto de 24 h das referências é
parte das 336 h, não um acréscimo. Ao atingir o orçamento global, preservar
checkpoints e estado e informar o autor, sem declarar uma grade incompleta
como concluída nem reduzir seu escopo para acomodá-la.

## 4. T19: substituição por idade com riscos concorrentes

Usar só a coorte auxiliar P0 materializada e disponível antes da origem. Para
cada contexto de aeronave, preservar o calendário/relógio inicial congelado
pela emenda 011 e seu peso w: número de canais observados desse P/N/aeronave.
Não usar trajetória avaliada, estado latente ou informação futura para calibrar.
P1 congela os parâmetros iniciais; P2_age usa os parâmetros mensais, mantendo
o calendário histórico de referência congelado.

Para um P/N, seja a seu limiar comum, u_j a exposição média diária do contexto
j (FH/dia, ou 1 na escala calendário), e nu a intensidade concorrente por dia.
Calcular u_j do vetor diário já produzido pelo construtor histórico, sem
preencher um calendário novo nem modificar o tratamento existente de dados.

Dos dias de visita distintos no ciclo histórico de duração D_j, formar os
intervalos positivos L, incluindo o fechamento cíclico entre a última visita
e a primeira do ciclo seguinte. Fixar a aproximação do excesso esperado:

    d_j = soma(L^2) / (2 * soma(L))
    T_j(a) = a / u_j + d_j
    S_j(t) = exp[-(u_j*t/eta)^beta - nu*t]
    h_U,j(t) = (beta/eta) * (u_j*t/eta)^(beta-1) * u_j

A taxa aproximada por contexto informativo é:

    C_j(a) = [ r * integral_0^T S_j(t) h_U,j(t) dt
                 + integral_0^T S_j(t) nu dt + S_j(T) ]
               / integral_0^T S_j(t) dt

A remoção concorrente tem custo unitário, como no avaliador vigente. A parcela
S_j(T) é a preventiva. Para a=infinito, remover essa parcela e integrar até
infinito. **Minimizar soma_j w_j*C_j(a)**, não a razão entre somas de custos e
durações e não um ótimo por aeronave. Os pesos são os mesmos da emenda 011.

Para beta <= 1, preservar a=infinito. Modelo/contexto indisponível mantém o
fallback vigente, sem inventar parâmetros ou visitas. Contextos sem visitas
não recebem prevenção. Exposição zero não entra em divisões por u_j; sua
contribuição independente do limiar permanece separada. O candidato a=0 deve
preservar o custo adicional de prevenir em todas as visitas também nesses
contextos, como no tratamento de fronteira da emenda 011. Esses componentes
não são retirados dos desfechos da simulação.

O deslocamento d_j supõe uma fase aproximadamente uniforme/independente da
renovação. Isso **não** reproduz a cadeia periódica exata: visitas, utilização
e renovações são dependentes na referência original. A aproximação é objeto
da verificação abaixo, não uma identidade demonstrada.

### Convenções numéricas propostas, anteriores ao cálculo

- Integração adaptativa: epsabs=1e-10 e epsrel=1e-8, com transformação da
  coordenada quando necessária junto a idade zero; exigir cauda de probabilidade
  <=1e-10 e duração residual <=1e-7 dia. Falha não vira um custo aceitável.
- Candidatos a=0, infinito e 129 idades logaritmicamente espaçadas entre
  eta*1e-6 e eta*1e3. Refinar cada mínimo local identificado na coordenada
  log(a/eta), com xatol=1e-8; comparar todos os candidatos.
- Essa é a busca numérica do **substituto aproximado**, não uma prova de ótimo
  global do problema de calendário. Mínimo finito em uma extremidade positiva
  do domínio é falha a informar, sem expandir ou reduzir a grade depois.
- Desempate dentro de 1e-12 na taxa: preferir infinito e, entre finitos, a maior
  idade. A grade experimental continua com 72 células; a malha do avaliador
  exato de verificação não é reduzida.

Na simulação, continuar a executar na primeira visita elegível segundo idade,
observabilidade e relógio permitidos na decisão. Não substituir visitas reais
pela data contínua T_j. MH, capacidade, conflitos e prioridade por recurso
permanecem as regras anteriores. Não mudar MILP, integração de custos dos
arcos ou custo terminal de P2/P3 para baratear a medição.

## 5. Verificação proposta: amostra e consequência fixadas antes de calcular

**N=9 contextos compostos (P/N, r)** da coorte já materializada
`data/derived/a9/warmup/replicas/pilot_amplified_0000`. Cada contexto composto
inclui **todas** as aeronaves daquele P/N com os pesos originais; não se
subamostram aeronaves para definir o limiar comum.

Semente **20261117015**, NumPy Generator(PCG64). Ordem fixa: r=(2,5,10), e para
cada r famílias=(rotor,wheels,vests). Em cada estrato, ordenar os P/N presentes
no domínio congelado e sortear uma posição uniforme. Isso produz nove pares
sem consultar ajuste, custo, ganho ou alarme. Congelar a lista, hashes da
coorte, calendários, pesos, parâmetros e avaliador antes da primeira avaliação.
Sem troca de casos, semente, tamanho ou exclusão após observar erro.

### Obtenção autorizada das referências ótimas exatas

Por decisão expressa do autor, esta revisão **autoriza o cálculo das referências
ótimas exatas** com o avaliador de calendário da emenda 011, na grade de
**1/4 de dia**, depois do commit que inicia o relógio. A autorização inclui a
busca necessária para certificar o ótimo global nessa discretização para cada
um dos nove contextos compostos. Não chamar de ótimo contínuo esse ótimo
na grade. Preservar os mesmos beta, eta, nu, r, contextos, pesos e controles
numéricos, de cauda e estacionariedade; não escolher outros parâmetros para
baratear a referência.

**Teto global de 24 h de parede nesta máquina, incluindo preparação e cálculo
das referências, dentro das 336 h.** O prazo começa no início da preparação
desse bloco, antes de sua primeira tarefa. Inclui seleção da amostra já
prescrita, preparação dos parâmetros/contextos, carga, cálculo e persistência
dos certificados. Não é um teto por contexto ou trabalhador e não reinicia
nas retomadas. Paralelismo não multiplica o tempo de parede disponível.
O bloco também deve respeitar o prazo global de 336 h, prevalecendo o prazo
que vencer primeiro. Seu consumo entra uma única vez no ledger global.

Persistir **checkpoints e certificados por contexto em disco**, identificados
pelos hashes dos dados, parâmetros, pesos, avaliador e configuração. Retomar
somente trabalho incompleto, preservando os certificados concluídos e o
prazo original. Ao completar todas as referências, congelar um **manifesto
completo das nove referências**, com idade ótima, taxa, grade, certificado
e hashes. **Nenhum limiar barato pode ser calculado antes desse manifesto
completo estar congelado e conferido.**

Se as referências necessárias não estiverem completas e certificadas em
24 h, **parar e apresentar o estado**, incluindo contextos concluídos/pendentes,
checkpoints, certificados e tempo consumido. Não reduzir a amostra, trocar
semente, parâmetros ou pesos, nem declarar a calibração validada com
referências ou resultados parciais. Não prosseguir à comparação da aproximação
ou à T20 nessa condição.

### Comparação da aproximação após congelar o manifesto

Depois de obter e congelar as nove referências, usar o mesmo avaliador
**somente nos dois pontos da comparação por contexto composto**: a_barato e
a_exato. A restrição a pontos isolados vale para esta comparação, não para
a obtenção dos ótimos exatos agora expressamente autorizada. Conferir a
compatibilidade dos certificados com os mesmos parâmetros, contextos, pesos,
avaliador e grade de 1/4 de dia. A comparação e os cálculos baratos subsequentes
consomem o saldo das 336 h; não recebem um orçamento adicional.

Registrar a taxa exata Q(a_barato), Q(a_exato), arrependimento relativo

    g = [Q(a_barato) - Q(a_exato)] / Q(a_exato)

nos mesmos grupos variáveis da referência, sem diluí-lo adicionando constantes.
Registrar também deslocamento absoluto/relativo do limiar, escala e todos os
ramos finito/infinito. Para duas idades infinitas, deslocamento zero; se só uma
for infinita, registrar a divergência de ramo, sem usar um número finito falso.
Referência de taxa zero não admite divisão: requer igualdade de taxa zero;
caso contrário a verificação é inconclusiva e para.

**Critério prospectivo:** g <= **0,005 (0,5%) em todos os nove contextos**,
sem divergência de ramo finito/infinito, sem falha numérica ou referência
incompatível. Arrependimento g < -1e-8 interrompe para conferir o certificado de ótimo;
valores entre -1e-8 e zero são relatados sem truncamento e não constituem
evidência de superioridade da aproximação. O deslocamento do limiar é relatado, não usado para escolher
uma tolerância depois dos resultados. Casos beta<=1 são controles analíticos;
não certificam sozinhos o ramo de envelhecimento. Sem caso informativo de
envelhecimento a verificação não é declarada aprovada.

Falha em qualquer caso **interrompe antes de T20**, para decisão do autor.
Não ajustar o método, amostra, domínio ou tolerância após a falha; qualquer
mudança exige outra emenda. Este controle de calibração é prospectivo e não
altera novamente a regra de encerramento da transferência T17.

### Histórico da autorização das referências

A versão anterior desta proposta constatou a ausência de uma tabela de ótimos
exatos certificados nos artefatos do piloto interrompido e não autorizava
busca global nova para obtê-los. Essa lacuna não foi preenchida por inferência
a partir de desfechos ou por uso de parâmetros diferentes.

A decisão do autor de 17/11 **substitui expressamente aquela restrição**:
a obtenção das referências passa a ser autorizada nos nove contextos já
fixados, com o teto global de 24 h e a persistência acima. Não altera a amostra,
a semente, parâmetros, pesos, avaliador ou critério g <= 0,005. A autorização
é prospectiva: esta revisão documental não executa o cálculo das referências.

## 6. Viés e limites de interpretação

A calibração mais grosseira de P1 **tende a favorecer P2** no contraste.
P2_age também recebe a aproximação; sua ablação não isola perfeitamente só a
escolha de visita se a calibração for inadequada. O teste de arrependimento
mede o viés de ajuste nos contextos amostrados, não um limite garantido do
ganho realizado em todos os meses/cenários ou sob capacidade conjunta.
A coorte auxiliar estacionária permanece no treino após deriva. Idade zero
no primeiro marcador, MH aproximadas da emenda 008, um operador e limitações
do gerador permanecem declarados. Nenhum resultado do simulador prova economia
real ou desgaste físico na frota.

## 7. T20, critério de escopo pré-fixado e execução depois do commit

O commit da emenda revisada, feito pelo autor, inicia o relógio de **336 h de
parede nesta máquina**. Dentro dele, implementar e testar em versão separada,
congelar fontes/configuração, calcular as referências com o subteto global
de 24 h e passar a verificação da seção 5. Só então perfilar uma réplica
pareada completa na célula 71, seis políticas, nesta máquina.

Manter **3 h exclusivamente como salvaguarda técnica contra travamento** da
réplica de perfilamento; o orçamento global de 336 h continua aplicável.
Persistir por etapa e mês, imediatamente em disco: parede, CPU, RSS, contagens
de ajuste A4, calibração, MILP, simulação e escrita. A réplica de perfilamento
fica fora de R e da inferência. Não abrir seus ganhos ou alarmes. Se ela não
terminar, preservar o estado e informar o impedimento técnico, sem inventar
uma duração completa ou previsão pontual.

### Projeção do restante e decisão fixada antes da T20

Medir t71 para a réplica completa na configuração de até oito processos.
Construir a lista das réplicas e etapas **ainda não executadas**, usando tempos
desta máquina. Se a execução principal não começou, faltam 72 * 200 réplicas
pareadas. Somar a elas apenas os ensaios técnicos, preparação e verificações
ainda pendentes, sem acrescentar operações já concluídas.

Definir, em unidades de tempo consistentes:

    C = tempo de parede já consumido desde o commit inicial
    T_base_restante = soma dos tempos projetados das réplicas e etapas ainda não executadas
    T_restante_projetado = 1,5 * T_base_restante
    saldo = 336 h - C

**Critério de escopo do autor, fixado antes da T20:**

    se T_restante_projetado > 336 h - C:
        parar a execução principal;
        adotar RQ4 como protocolo mais piloto de viabilidade;
        deixar a avaliação completa como trabalho futuro.

O consumo C — referências exatas, verificação da calibração, T20 e tudo o mais
desde o início do relógio — entra **somente no lado direito**, abatendo o saldo.
Não o somar outra vez a T_restante_projetado, não aplicar a reserva a C e não
projetar novamente a réplica de perfilamento já executada. Como o perfilamento
é fora de R, sua exclusão da lista de etapas futuras **não retira uma réplica
da grade principal**: se nenhuma principal foi executada, continuam faltando
14.400 réplicas principais. O tempo t71 já contém seis políticas e o paralelismo
interno; não multiplicar novamente por seis nem dividir por oito.

As cinco réplicas de piloto já previstas continuam como ensaio técnico fora
da inferência e não selecionam R. Na projeção, incluir somente as ainda
pendentes; qualquer retirada desse ensaio exige decisão expressa. Uma célula
não certifica a distribuição de tempos das demais: declarar essa limitação
da projeção, preservando a reserva de 1,5 e registrando os tempos efetivos.

Ao fim da T20, parar para apresentar consumo, saldo, projeção restante e o
resultado do critério pré-fixado. Se não couber, não executar uma subgrade:
a grade completa (72 células, seis políticas, R=200) é a **única execução
principal autorizada**. Não reduzir automaticamente células, políticas ou R,
nem escolher outro caminho depois de ver os resultados. O artigo deverá
distinguir RQ1–RQ3 concluídas da RQ4 não respondida, ajustar objetivo e
contribuições e não afirmar ganhos econômicos ou prescritivos não demonstrados;
essa edição cabe ao Claude após a decisão, não a esta revisão documental.

### Execução principal, se a grade completa couber

A implementação nova deve usar diretórios/configurações separados para o
orçamento de 336 h e o critério acima. Os antigos stops por 60/120 h, a seleção
automática de R e o certificado antigo de inviabilidade por orçamento não são
reutilizados como política vigente. Os executores/configurações históricos
continuam intactos. A decisão intermediária sem teto também permanece somente
no histórico; não autoriza exceder as 336 h da decisão posterior.

Na grade principal: índices 0..199 por célula; sementes independentes da ordem
de execução; checkpoint atômico e manifesto de conclusão por réplica;
retomada sem refazer réplicas finalizadas/verificadas; progresso periódico;
falhas preservadas, nunca substituídas silenciosamente por outra semente ou
excluídas da grade. Uma falha persistente não conta como conclusão verificada.
O consumo global deve continuar sendo acompanhado até a verificação final.
Esgotadas as 336 h, preservar o estado e informar o autor, sem extensão
silenciosa, redução automática de escopo ou declaração de conclusão parcial
como se fossem as 14.400 réplicas e seis políticas completas. Nenhuma análise
adicional é aberta sem ligação com uma RQ e aprovação.

**Parada desta rodada:** proposta revisada entregue para auditoria, sem
execução de cálculos, perfilamento ou experimentos e sem commit. O relógio
de 336 h só começa no commit da emenda revisada, feito pelo autor.


## Adendo de 19/11/2026 — execução adicional única e isolada de 06

Por decisão expressa do autor, registrada em `docs/tarefas_codex.md` após o
vencimento do subteto original em 2026-11-19T16:16:40Z, fica autorizada uma
única execução adicional do contexto 06 (P/N 3G6430A00335, r=10), isolada e
recomeçando do zero. A decisão foi tomada após observar 8/9 referências
certificadas e a telemetria de 06 (100% das fases e 65,47% das quebras), sem
informação de ganhos, alarmes ou calibração barata. É um desvio prospectivo
para esta execução adicional, posterior ao resultado de incompletude das 24 h.

O teto rígido é de 8 h de parede desde o início da preparação desta execução,
registrado no ledger em **2026-11-19T16:52:47.754961+00:00**, até
**2026-11-20T00:52:47.754961+00:00**, dentro das 336 h e sem reinício em retomadas.
O intervalo é debitado uma única vez do orçamento global iniciado em
`2d7e19d`, 2026-11-18T15:57:28Z. O prazo global permanece
2026-12-02T15:57:28Z. Os tetos e resultados anteriores permanecem no histórico.

Preservar o código numérico e a configuração congelada de 06: memmap já
testado byte a byte, float64, grade de 1/4 de dia, controles numéricos,
parâmetros, pesos, semente, amostra e desempates. Usar a mesma telemetria
somente de leitura. Não reaproveitar estado parcial da varredura; os oito
certificados existentes permanecem intactos. Não executar outro processo
do executor em paralelo. A única alteração de controle é o prazo adicional
expressamente autorizado; o subteto original não é reaberto ou reescrito.

Se 06 concluir dentro das 8 h, congelar e conferir o manifesto completo
das nove referências e parar para auditoria antes de g <= 0,005.
Se não concluir, interromper no prazo sem nova extensão, apresentar estado
e telemetria e manter a calibração não validada. Nesse caso, por decisão
do autor, a RQ4 passa a protocolo mais piloto de viabilidade, com avaliação
completa como trabalho futuro, conforme a seção 7. Não reduzir grade,
políticas, R, amostra ou precisão. Não iniciar a verificação, T20, ensaio
técnico ou execução principal nesta autorização. Não fazer commit.

Este adendo é acrescentado ao fim do documento; os bytes do texto commitado
em `2d7e19d` são preservados como prefixo, sem edição retroativa.


## Adendo de 20/11/2026 — encerramento de A9/A10 pela regra de escopo

A verificação da calibração foi aprovada nos nove contextos (9/9, maior
g = 0,00108519). A salvaguarda interrompeu a T20 em 10 800 s. P0, P1, P2
e P3 completaram os 24 meses, P2_fixed completou 15/24 e P2_age ficou por
iniciar. Como as seis políticas rodavam em sequência, **t71 > 10 800 s**
é um piso medido. A duração completa permanece desconhecida.

O [relatório da T20](a9_amendment015_T20_report.md) registrou C = 46,89 h
e saldo de 289,11 h. Nas condições da seção 7, a execução principal
exigiria uma duração média de até 289,11 h / (1,5 × 14 400) ≈ 48 s por
réplica, cerca de 224 vezes abaixo do piso. O limite inferior do tempo
restante ainda fica em aproximadamente 2 600 h sem a reserva de 1,5,
com seis trabalhadores e células dez vezes mais rápidas. O commit
`19bd43d` registra a correção aritmética de 72 s e 150× para 48 s e 224×
na aplicação da reserva.

O relatório original da T20 classificou o critério como **não avaliado**
porque a réplica pareada ficou incompleta. Depois da interrupção, o autor
declarou cumprido o critério da seção 7 por limite inferior, sem acesso
aos desfechos e sem extrapolar os tempos parciais. A RQ4 fica como
**protocolo mais piloto de viabilidade**, com a avaliação completa como
trabalho futuro. A9/A10 foram encerradas. O ensaio técnico, a execução
principal, uma subgrade e nova T20 ficaram sem execução. Ganhos e alarmes
da réplica de perfilamento permanecem fechados e fora da inferência.
O [relatório final](a9_amendment015_final_report.md) registra o encerramento
e remete aos artefatos preservados.
