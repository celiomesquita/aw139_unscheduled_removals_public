# Emenda A16/A9_012 — interrupção por limite computacional demonstrado

14/11/2026. **Autorizada explicitamente pelo autor antes da interrupção.**
O autor respondeu “Autorizo” à proposta apresentada. A interrupção do piloto
da emenda 011 e a otimização equivalente estão autorizadas. Esta emenda
é posterior ao conhecimento de tempo parcial de execução, sem abertura de
custos, ganhos, alarmes ou comparações de políticas do piloto.

## Evidência concreta

O piloto começou às 21:58:15 UTC de 14/11/2026, PID 15052, configuração
5af0d2cbd5fd559f8a2e15f0a3dd5e50f4773ed5dfbdcfbc9b462ba2da4a278c.
A réplica 0 permanece incompleta na calibração de P1. Não existe checkpoint
final dessa réplica e nenhuma das cinco medições completas foi obtida.

observe_a9_budget.py registrou dois instantes de relógio monotônico dentro da
mesma réplica inacabada, no mesmo processo vivo e configuração. O intervalo
foi 82,1790401 segundos. Logo, a duração completa dessa réplica é maior que
esse valor, independentemente do restante do processamento. O observador
não interrompeu o piloto e não abriu resultados de políticas.

Pela fórmula fixada, R≥200 em 72 células, com reserva 1,5 e 120 h, requer
t_piloto ≤ 120×3600/(72×1,5×200) = **20 segundos**. Como o maior dos cinco
tempos completos será pelo menos o tempo completo da réplica 0, o orçamento
é demonstravelmente insuficiente para a implementação atual. Isso é um limite
inferior de tempo e um certificado de inviabilidade orçamentária; não é uma
estimativa pontual do tempo completo nem uma seleção de R.

Prova em data/derived/a9/pilot/budget_lower_bound.json. Nenhuma réplica parcial
substitui as cinco réplicas completas exigidas para fixar R. O pré-registro
original e a emenda 011 continuam preservados.

## Ação autorizada

1. Interromper apenas o processo deste piloto, conferindo PID, linha de comando
   e configuração; preservar estado, logs, tempos, histórico auxiliar e a
   réplica parcial, identificada como interrompida por inviabilidade computacional.
2. Não selecionar R e não iniciar a execução principal. Não interpretar ganho
   ou ausência de ganho a partir do piloto parcial.
3. Otimizar a implementação com operações equivalentes, preservando grade,
   R mínimo, estimandos, custos, enumeração admissível, tolerâncias, sementes,
   observabilidade, aquecimento e regras de detecção. Não reduzir o problema
   científico nem substituir a calibração por uma regra mais favorável.
4. Exigir igualdade de resultados entre versões em testes completos e medir
   desempenho nas mesmas entradas. Não prometer que a aceleração tornará o
   orçamento suficiente antes dessa medição.
5. Se retomado, usar uma configuração e diretório novos, preservando o piloto
   atual; manter as cinco sementes pré-especificadas e reutilizar os históricos
   auxiliares já gerados, sem novos sorteios. As cinco réplicas completas ainda
   serão necessárias para fixar R na implementação otimizada.

Os custos computacionais parciais permanecem no registro acumulado; o orçamento
de 120 h não é reiniciado. Qualquer necessidade de orçamento adicional continua
uma decisão do autor. A autorização explícita foi recebida; esta emenda não
declara concluído o piloto.
