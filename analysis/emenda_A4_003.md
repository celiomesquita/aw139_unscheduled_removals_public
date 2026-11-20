# Emenda A4_003 — esclarecimentos após a primeira execução completa

Data: 12/11/2026. Escrita com os resultados principais já conhecidos:
K2-A4 misto e K2-idade nulo. Não houve nova escolha de modelo ou ajuste aos
dados para obter outro resultado. O pré-registro permanece preservado.

1. A sensibilidade de limites ampliados foi executada incondicionalmente,
   inclusive sem fronteira superior no principal, em vez de apenas quando
   exigida pela condição do protocolo. Foi listada no código antes de calcular
   os resultados e também produziu K2-A4 misto/K2-idade nulo. Não substitui o
   principal; não introduziu seleção retrospectiva de limites.
2. O manifesto do executor contém hashes e revisão do pré-registro. As versões
   do ambiente e a revisão da execução são acrescentadas em environment.json
   pelo verificador de reprodução, depois de conhecida a primeira decisão.
   Trata-se de metadados, sem mudar ajuste, previsões ou critérios. O verificador
   compara todos os artefatos de duas execuções completas e confere a igualdade
   da base e dos alvos com A5 na mesma população.
   O índice a4_input_supplement.json completa os hashes dos insumos auxiliares
   de sensibilidade (mapa T2 e referências das correções administrativas) e dos
   arquivos de verificação; é metadado suplementar, não uma reexecução seletiva.

Essa complementação não é evidência adicional de ganho preditivo. O resultado
negativo da idade e K2 nulo de A5 são preservados.
