# A3 — validação documental dos intervalos propostos

Execução: `py -3 analysis/inspection_evidence.py`, após `inspection_censoring.py`.

## Regras e rastreabilidade

Auditoria das dez propostas de intervalo de tesouras. Pesquisa na descrição da
discrepância no documento atual: componente, detecção, tarefa nominal e condição
próxima/no limite versus limite excedido. Os indicadores devem coexistir na
mesma descrição de componente; não se usa o resultado satisfatório de uma
substituição como prova da condição anterior. A inspeção prévia precisa registrar
resultado satisfatório; documentos com achados de tesouras não sustentam o proxy
de inspeção negativa. Datas recuperadas por mediana do documento mantêm a
limitação da extração OMTH. Regras explícitas em `description_flags` e `audit`.

## Resultado

| verdict                                          |   events |
|:-------------------------------------------------|---------:|
| detection_by_different_or_unspecified_inspection |        6 |
| preventive_margin_not_confirmed_failure          |        4 |

Inspeção anterior com resultado satisfatório: 10/10.
Proxy de inspeção anterior negativa, sem achado de tesoura no documento:
10/10.
Detecção menciona nominalmente a tarefa proposta: 2/10.
Descrição menciona substituição próxima/no limite: 4/10.
Descrição menciona limite excedido: 6/10.

## Consequência científica

O rótulo UNSCHEDULED não equivale automaticamente a falha: pode incluir retirada
por margem preventiva. A coincidência documental não identifica a inspeção
detectora. A sensibilidade Weibull anterior continua reproduzível, mas não
confirma desgaste de um modo de falha fisicamente definido nem aprova K1.
Antes de A5, definir o endpoint (remoção não programada versus falha funcional)
e auditar os rótulos da coorte. Se o endpoint for remoção, os parâmetros descrevem
o processo de remoção sob a política observada; não são automaticamente uma lei
de vida física transferível ao contrafactual de substituição preventiva.
Revisão de unidade e modo de falha continua necessária mesmo para candidatos
com suporte documental; expressões regulares não constituem validação física.

Evidência por trecho e referências documentais: `data/derived/inspection_evidence.csv`.
Nenhum texto livre ou nome de funcionário é exportado.
