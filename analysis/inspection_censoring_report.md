# A3 — censura intervalar: associação documental e sensibilidade

Execução: `py -3 analysis/inspection_censoring.py`, após `analysis/feasibility.py`.
Coorte principal, instalações dentro da janela; sem extrapolação pré-2024.

## Protocolo e alcance

Mapa explícito P/N–tarefa em `inspection_censoring.py`: tesouras de rotor
principal e amortecedores. Parafusos, terminais e inspeções genéricas de célula
não recebem associação presumida. Exige mesma aeronave e documento; regra
estrita: assinatura no dia da remoção. Sensibilidade exploratória: assinatura
até três dias antes/depois, sem alterar a data da remoção. A tolerância foi
introduzida após observar defasagem administrativa; não é confirmatória.
Regra estrita: 0 intervalos propostos;
tolerância de três dias: 10 intervalos propostos.
Limite inferior: ocorrência anterior da MESMA tarefa, em outro documento, durante a
instalação. Limite superior: remoção. Usa FH não arredondadas artificialmente
por clipping, mas provenientes do relógio diário exportado pela viabilidade.
Eventos não associados permanecem exatos na sensibilidade. Compara ajustes na
mesma coorte com e sem intervalos; idades FH nulas são excluídas de ambos e
contabilizadas. IC 95% Wald em log beta, sem correção de dependência por aeronave.

## Cobertura dos eventos ATA 62

| status                                  |   events |
|:----------------------------------------|---------:|
| no_document_inspection_within_tolerance |      133 |
| unmapped_component                      |       79 |
| provisional_interval                    |       10 |

## Ajustes exploratórios (FH)

| pn           | mode                |   spells |   events |   intervals |   zero_age_excluded |   beta |     eta |   beta_lo |   beta_hi | converged   |
|:-------------|:--------------------|---------:|---------:|------------:|--------------------:|-------:|--------:|----------:|----------:|:------------|
| 3G6230A00833 | exact               |      106 |       85 |           0 |                   2 | 3.0852 | 330.303 |    2.6889 |    3.5399 | True        |
| 3G6230A00833 | inspection_interval |      106 |       85 |          10 |                   2 | 2.9181 | 324.68  |    2.5285 |    3.3677 | True        |

## Limites e decisão

Associação no mesmo documento NÃO comprova que a falha foi detectada pela
tarefa, nem que a inspeção anterior foi negativa para o modo de falha relevante.
O mapa de aplicabilidade e os resultados anteriores ainda precisam de validação
documental. Estes intervalos são hipóteses de sensibilidade, não observações
intervalares confirmadas. Não aprovar K1 nem retirar candidatos automaticamente.
Sem essa validação A3 permanece parcial, e os IC não constituem inferência final.
Validação documental complementar: [auditoria dos intervalos](inspection_evidence_report.md),
gerada por `analysis/inspection_evidence.py`. Consultar essa auditoria antes
de interpretar os intervalos como falhas confirmadas.
Não comparar AIC entre os ajustes exato e intervalar: a observação modelada muda.
Artefatos detalhados: `inspection_intervals.csv` e `inspection_weibull_fits.csv`
em `data/derived/`. Nenhum texto livre do operador é exportado.
