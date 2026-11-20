# Emenda A5_001 — convenções de implementação, antes da execução

Pré-registro preservado: `preregistro_A5.md`, A5_v1, commit aed4c3a.
Data: 12/11/2026. Nenhuma previsão ou decisão K2 foi calculada ao redigir esta emenda.

1. **Dias e horizontes.** Origem é início do dia; corte é fim do dia anterior.
   Avaliação usa [origem, origem + meses), incluindo remoção na origem e excluindo
   a data inicial do período seguinte. Idade de calendário no corte é diferença
   entre as datas de corte e instalação, ambas na convenção de fim do dia.
   A janela de utilização contém exatamente os 90 dias terminados no corte.
2. **Integração.** Incidência concorrente usa quadratura Gauss–Legendre com 48
   nós, transformada para a probabilidade não concorrente, evitando a singularidade
   da hazard Weibull na idade zero. Exponencial tem fórmula analítica. Sensibilidade
   com FH realizadas integra incrementos diários, mantendo a ordem dos voos e
   a monotonicidade no horizonte; não usa a taxa média realizada de cada horizonte.
3. **Campos de horas ausentes.** A escala FH conserva a convenção da viabilidade:
   acumula horas registradas; ausência não é evidência de voo nem é contabilizada
   como hora conhecida. Exportar cobertura. Taxa principal sem qualquer registro
   de horas nos 90 dias aciona previsão em calendário; taxa zero observada é zero.
4. **Decolagens.** Além do trecho desde a instalação, a janela de previsão de
   90 dias precisa ter contadores completos. Na imputação, aplicar a razão do
   treino aos registros com decolagens ausentes e horas conhecidas; se ambos
   faltarem, continuar ausente. Fallback preserva os casos de avaliação.
5. **Sensibilidades.** Executar cada uma isoladamente contra o principal, com
   seleção interna e ajustes próprios, sem combinar retrospectivamente as mais
   favoráveis. Proveniência confirma instalação pelo registro de substituição
   na mesma aeronave/P/N/serial, até três dias da instalação e ocorrido até o corte.
6. **Mapa T2.** Intervalos por inspeções anteriores ao corte são construídos em
   cada escala; largura zero mantém a observação exata, como em T2, com marcador.
   Os limites não são datas físicas de falha confirmadas. Não se usa o genérico
   de 86,75 FH como sensibilidade adicional não prevista em A5.
7. **Bootstrap e saídas.** Usar os 24 códigos de aeronave, preservando blocos;
   grupos sem observações ficam ausentes, não zero. Partilhar os mesmos sorteios
   entre comparações e sensibilidades. Registrar ausência por P/N. Na calibração,
   os decis são calculados separadamente por modelo/variante sobre previsões
   externas, com desempate por origem, horizonte e ID do trecho.

Estas convenções resolvem detalhes não especificados no pré-registro, sem mudar
população, comparadores, métricas ou critério K2. O arquivo original não foi editado.
