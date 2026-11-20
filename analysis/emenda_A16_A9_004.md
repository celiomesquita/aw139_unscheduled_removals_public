# Emenda A16/A9_004 — executor principal e retomada determinística

13/11/2026. Protocolo aa129e2 e emendas 001–003 preservados. Definida após o
commit 9c1a0ee da decisão do autor de 60 h para A16 e antes de qualquer resultado
principal de poder ou erro tipo I. Nenhuma hipótese, grade ou regra é alterada.

## Configuração anterior aos resultados

R=200, calculado pela fórmula original com 60 h e o máximo do piloto original.
Não repetir o piloto para obter R mais conveniente. Congelar configuração,
hashes, versões, orçamento, sementes, grade e unidade de inferência antes da
primeira réplica principal. Os efeitos ajustados são os mesmos modos de A4;
a transformação média-preservada de η da versão commitada permanece.

O piloto executou internamente métricas e bootstrap para medir seu custo, como
descrito na emenda 002; resultados foram descartados, sem tabelas inspecionadas,
retidas ou usadas para escolher R. Este registro distingue chamadas de funções
da produção de estimativas de poder/erro tipo I, que ainda não existiam.

## Ordem e sementes

Concluir primeiro as três células β=1, tamanhos ×1, ×2 e ×4. Em cada célula,
executar todas as 200 réplicas e ambas as variantes antes de avaliar a parada
de erro tipo I >0,10, agregado ou familiar. Não parar por frequência parcial
de rejeição. Se as três passarem, executar modos A4 e β ampliado, em ×1/×2/×4.

Chave SeedSequence principal: [20261112,16,célula,réplica,P/N,aeronave,canal,cópia,risco].
Célula = 3×índice_nível + índice_tamanho, com níveis [calibrated,null,amplified]
e tamanhos [1,2,4]. A ordem computacional não altera esses índices. O piloto
continua com fluxo 160 e sua chave histórica; seus dados não são reutilizados.
A extensão opcional da função synthetic_inputs conserva exatamente o padrão
anterior quando chamada pelo piloto. Bootstrap continua PCG64/20261112, B=999.

## Método, checkpoint e falhas

Reutilizar PilotEvaluation e os métodos de A4/A5. O cache já declarado na emenda
002 só compartilha treino idêntico na mesma origem entre as duas variantes.
Salvar previsões, métricas, calibração, intervalos, ajustes e hiperparâmetros
por réplica. Treino compartilhado é rotulado como comum às variantes; previsões
retêm rótulos separados. Nenhuma informação futura passa ao ajuste.

Previsões e diagnósticos volumosos ficam locais, com manifestos SHA256; os
resultados por réplica e agregados ficam em CSV/JSON rastreáveis. Escrita de
resumo final por réplica é atômica. Após interrupção, retomar somente réplicas
sem resumo final e com a mesma configuração/código; nunca repetir uma réplica
com falha registrada para substituí-la por sucesso. Guardar falhas no denominador
como não detecção e reportar limites se todas as falhas fossem detecções.

Wilson 95% e erro Monte Carlo para agregado, família (qualquer P/N) e cada um
dos 11 P/N. Famílias usam exatamente os limites Bonferroni de A4; não ajustar
novamente por quantidade de réplicas. Se toda uma célula/variante falhar, o
controle é não avaliável e a interpretação para, em vez de erro tipo I zero.
Relatar fallbacks e convergências separadamente das falhas de execução.

## Execução prolongada

Um único processo de cálculo, em segundo plano sem janela, com lock por PID,
log, estado/heartbeat e relatório atualizado ao completar cada célula. O processo
preserva saídas históricas A4/A5/pré-registros e verifica hashes nas fronteiras
das células. Excesso de 60 h é registrado sem parar por significância, conforme
emenda 003. O executor termina ao concluir A16 ou ao atingir parada de calibração;
não lança A9/A10 automaticamente. Sua conclusão sinaliza a próxima etapa de T12.
