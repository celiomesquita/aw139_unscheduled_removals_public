# Emenda 015 — verificação da calibração por idade

**Resultado: aprovada nos nove contextos**, sem alteração de método, amostra, pesos, parâmetros, avaliador ou tolerância. Critério: −1e-8 ≤ g ≤ 0,005; ramos finito/infinito coincidentes.

Q é a soma ponderada das taxas exatas nos grupos variáveis da referência, sem constantes adicionais. A avaliação usa a grade de ¼ de dia e o mesmo avaliador histórico; 06 usa o armazenamento memmap já testado.

| Contexto | P/N | r | Q(a_barato) | Q(a_exato) | g | Resultado |
|---|---|---:|---:|---:|---:|---|
| 00 | 3G6230A00833 | 2 | 0.26780227700884091 | 0.26775259755590292 | 0.00018554237528028921 | aprovado |
| 01 | 3G3240V01731 | 2 | 0.04001050647940689 | 0.040007065416098164 | 8.6011390061655271e-05 | aprovado |
| 02 | S-7200-514-PAX | 2 | 0.768827592416364 | 0.76882671099208544 | 1.1464537664508004e-06 | aprovado |
| 03 | 3G6230A00833 | 5 | 0.41156975843057736 | 0.41114081902925514 | 0.0010432907205248651 | aprovado |
| 04 | 3G3240A07531 | 5 | 0.97289563969615089 | 0.9727687193167408 | 0.00013047333542883283 | aprovado |
| 05 | S-7200-514-PLB | 5 | 2.9499000573220009 | 2.9495749997160647 | 0.00011020489594854958 | aprovado |
| 06 | 3G6430A00335 | 10 | 0.097256071676270622 | 0.097253483585127171 | 2.6611809140865597e-05 | aprovado |
| 07 | 3G3240A07531 | 10 | 1.4680477239814895 | 1.4664563355137539 | 0.0010851932165972967 | aprovado |
| 08 | S-7200-514-PAX | 10 | 1.6685571419092915 | 1.6685571419092915 | 0 | aprovado |

Maior g: 0.0010851932165972967; maior diferença absoluta entre Q(a_exato) recalculado e a taxa do certificado: 1.7291723608536813e-13.

Os limiares, deslocamentos, ramos e diagnósticos completos estão em `data/derived/a9/amendment015/verification_table.csv`, `verification/00.json` a `08.json` e `verification_manifest.json`. O manifesto das nove referências e os certificados permaneceram intactos.

A entrada separada `analysis/amendment015_authorised_verification.py` reconhece a exceção das referências auditada pelo autor e o prefixo commitado do documento, sem reabrir o prazo original nem alterar os módulos numéricos congelados. Dois controles de integridade passaram: exceção aprovada aceita, divergência de hash numérico rejeitada.

Uma correção exclusivamente de metadados do ledger substituiu o padrão que marcava a conclusão das referências na data de lançamento da verificação pelo instante real do checkpoint final de 06. O valor anterior e a razão estão preservados em `verification_reference_timestamp_correction.json`. C continua sendo apenas o tempo corrido desde o commit, sem somar durações de etapas.

Nenhum ganho ou alarme A9/A10 foi aberto. A aprovação autoriza prosseguir à T20 nesta mesma instrução do autor; ensaio técnico e execução principal continuam não iniciados. Nenhum commit.
