# Auditoria ampliada dos desfechos — A2/A3 e condição de A5

Execução: `py -3 analysis/removal_labels.py`, após a viabilidade.

## População e protocolo

Todos os 11 P/N com IC de beta acima de 1 na viabilidade,
incluindo 661 remoções não programadas da coorte principal.
Vínculo por P/N, serial, aeronave, instalação e remoção; procura diagnóstico NST
na mesma aeronave e documento, assinatura dentro de ±3 dias. Referência ao
componente por P/N, serial ou vocabulário explícito em `COMPONENTS`.
Somente `Task Description` é usada para condição; resultados satisfatórios de
reparo não viram prova de ausência de falha. Dados originais não são alterados.
As classes são indícios documentais, não rótulos físicos confirmados.

## Resultados

| category                         |   removals |
|:---------------------------------|-----------:|
| damage_evidence                  |        201 |
| condition_unspecified            |        161 |
| no_component_diagnosis_within_3d |        154 |
| exceeded_evidence                |        135 |
| margin_evidence                  |          9 |
| functional_evidence              |          1 |

| Part #          |   condition_unspecified |   damage_evidence |   exceeded_evidence |   functional_evidence |   margin_evidence |   no_component_diagnosis_within_3d |
|:----------------|------------------------:|------------------:|--------------------:|----------------------:|------------------:|-----------------------------------:|
| 3G3240A07531    |                      78 |                18 |                  53 |                     0 |                 0 |                                  7 |
| 3G3240V01731    |                      23 |                 3 |                  24 |                     0 |                 0 |                                  1 |
| 3G6220A01252    |                       2 |                 8 |                   0 |                     0 |                 0 |                                 13 |
| 3G6220V02051    |                       1 |                13 |                   0 |                     0 |                 0 |                                  5 |
| 3G6230A00833    |                      14 |                 1 |                  45 |                     0 |                 7 |                                 18 |
| 3G6230A00932    |                       1 |                 2 |                  10 |                     0 |                 0 |                                  6 |
| 3G6230A00934    |                       2 |                 0 |                   2 |                     0 |                 2 |                                  6 |
| 3G6430A00335    |                       5 |                 4 |                   1 |                     0 |                 0 |                                  4 |
| M006-01H095-043 |                       5 |                21 |                   0 |                     0 |                 0 |                                  3 |
| S-7200-514-PAX  |                      12 |                64 |                   0 |                     1 |                 0 |                                 23 |
| S-7200-514-PLB  |                      18 |                67 |                   0 |                     0 |                 0 |                                 68 |

## Regras, limites e decisão

Margem, limite excedido e indicação funcional concomitantes no mesmo documento
produzem classe mista. Dano/corrosão/vazamento é indício de condição, sem
pressupor perda funcional. Documento sem diagnóstico pertinente não constitui
evidência negativa. Vocabulário e tolerância são exploratórios e incompletos.
Mesmo P/N ou serial citado pode referir-se à unidade instalada; associação
por família pode referir-se a outra posição/unidade. Requer revisão por unidade,
modo e limiar; negações e condições compostas podem escapar às regras.
Não usar essa triagem automaticamente para excluir eventos, tratar retiradas
como censura independente, estimar taxa de falha funcional ou aprovar K1/K2.

A5 pode prever o endpoint operacional de remoção registrada, mas isso não
identifica a distribuição de vida física necessária ao contrafactual de A7–A9.
Próxima etapa: adjudicar diagnósticos mistos/ambíguos e recuperar a inspeção
detectora e datas de achado a partir dos documentos referenciados. Falhas
funcionais devem ter critério operacional explícito, não somente uma palavra.

Rastreabilidade sem texto livre: `removal_label_audit.csv`,
`removal_label_evidence.csv` e `removal_label_summary.csv` em `data/derived/`.
As contagens são por remoção, não por documento independente.
