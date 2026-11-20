# A9/A10 — integração das políticas e início do piloto

14/11/2026. Emenda 011 fixada antes de qualquer observação avaliada do piloto.
O aquecimento segue integralmente a emenda 010. A16, A5/A4 e seus resultados
originais permanecem preservados; parâmetros verdadeiros continuam os de A4
original, sem retuning a partir da errata ou do piloto.

## Implementação

- P1: minimização determinística da taxa esperada de custo no calendário
  histórico, cadeia de renovação de Markov por fase, enumeração dos pontos
  de mudança de visita e opção somente corretiva. Há limites de cauda e
  refinamento temporal. O certificado é para a discretização declarada.
- Detecção: IC Wald de log η a partir da informação conjunta de médias e
  efeitos, condicionado às variâncias estimadas. Variância aleatória nula
  não elimina a incerteza da média. Informação inválida é não avaliável.
  A incerteza dos componentes de variância não é propagada nessa aproximação.
- P0, P1, P2, P3, P2_fixed e P2_age integram eventos, observações, ajuste mensal,
  previsões, visitas e capacidade. Custos incluem renovações sucessivas e o
  ciclo terminal; este último tem verificações separadas de cauda e quadratura.
- O eixo previsto usa apenas o passado; o conhecido recebe o caminho exógeno
  autorizado. P3 conhece os parâmetros vigentes, sem antecipar η futuro nem
  os limiares aleatórios. Instalações latentes não observáveis não fornecem idade
  ao estimador ou à política. Preventivas são conferidas contra a capacidade
  efetiva na execução, além da restrição do MILP.

## Verificação

Dois fluxos completos pequenos, cada um com as seis políticas, foram repetidos
com identidade dos eventos, custos e alarmes. Há um cenário sem envelhecimento
e outro com envelhecimento e preventivas. Esses são testes artificiais com
parâmetros conhecidos e um adaptador de ajuste fixo; não são réplicas da frota
nem prova empírica de reação à deriva. Recuperação de parâmetros do estimador
hierárquico permanece coberta pelos testes A4 da suíte completa.

Passaram 172 testes da suíte completa em 280,163 segundos. Um novo teste de
P1 encontrou uma fronteira não enumerada: um limiar positivo imediatamente
acima de zero podia evitar preventivas em aeronaves sem utilização sem mudar
a visita elegível nas demais. A implementação anterior e a prova da primeira
suíte estão arquivadas. Após a correção isolada, todos os 44 testes de A9 e as
duas repetições de integração passaram. As demais fontes verificadas são as
mesmas da suíte completa, conferidas por hash; não se apresenta o teste novo
como parte da primeira rodada. Não houve comparação financeira da frota.

Provas em data/derived/a9/integration_verification.json e
integration_before_zero_exposure_fix.json. Metadados históricos de replay
restaurados, hashes protegidos conferidos e manuscrito preservado.

## Piloto iniciado

Configuração congelada:
5af0d2cbd5fd559f8a2e15f0a3dd5e50f4773ed5dfbdcfbc9b462ba2da4a278c.
Início: 14/11/2026 às 21:58:15 UTC, 18:58:15 de São Paulo. Coordenador PID
15052, em segundo plano, sem janela. Cinco réplicas completas previstas,
célula 71, seis políticas por réplica, sem salvar ou abrir ganhos/alarme.
O executor não inicia a rodada principal automaticamente.

O estado em data/derived/a9/pilot/state.json é a fonte de progresso. O tempo
de uma etapa não é uma medição completa e R ainda não foi selecionado.

## Limite de orçamento demonstrado sem resultados de políticas

A fórmula de 120 h, 72 células, reserva 1,5 e R≥200 exige t_piloto≤20 s.
Dois pontos de relógio monotônico dentro da mesma réplica ainda incompleta,
no mesmo processo vivo, mediram intervalo de 82,1790401 s. Portanto a maior
duração completa do piloto será superior a esse limite e a implementação
atual não comporta o mínimo no orçamento. Não foi estimado seu tempo completo
nem fixado R usando essa medição parcial.

O observador não interrompeu o piloto. Depois, o autor autorizou a
[emenda 012](emenda_A16_A9_012.md), e a execução original foi encerrada com
seu estado parcial e fontes preservados. Fonte da prova de orçamento:
data/derived/a9/pilot/budget_lower_bound.json. A versão otimizada e sua retomada
estão documentadas separadamente em a9_optimisation_report.md e na emenda 013.
