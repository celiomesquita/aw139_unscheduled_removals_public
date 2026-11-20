# A9/A10 — execução e verificação da emenda 010

14/11/2026. A emenda 010 foi escrita e a configuração congelada antes da
primeira observação auxiliar. Nenhuma observação de avaliação ou réplica de
piloto foi gerada. As gerações desta entrega são do fluxo de verificação,
excluído do piloto e da inferência.

## Desenho implementado

Coorte auxiliar P0 estacionária, com canais e relógios do primeiro ano
deslocados exatamente 365 dias. Entradas tardias e máscaras de observação
mantidas, sem gerar idade anterior ao primeiro marcador. O fluxo 90 separa
verificação, piloto e execução principal; a chave inclui nível de β, réplica,
P/N, aeronave, canal, renovação e risco. O gerador não recebe política, r,
cenário ou conhecimento de utilização como argumento.

O histórico é materializado uma vez por réplica e fornecido em cópias
idênticas às seis políticas. As células com o mesmo nível de β e réplica
compartilham o aquecimento. Arquivos existentes são lidos e conferidos por
hash; não há novo sorteio para outra política. Suas censuras ficam fixas,
e os registros permanecem no treino após o primeiro ajuste e após a deriva.

Os relógios auxiliares têm identificadores separados dos avaliados: não
somam utilização sobreposta nem preenchem a utilização ausente na avaliação.
Como 2024 é bissexto, a extremidade deslocada pode chegar a 01/01/2024.
Essa observação não é antecipada para o ajuste dessa origem; continua valendo
o corte exclusivo. Idades de calendário de canais sem registro de voo são
preservadas sem inventar uma linha de voo zero conhecido.

## Evidência de verificação

Configuração SHA-256:
8a50f170893f3da95586c08b69966af2eba68e21de79f504ad7526d4f8e97eec.

- Duas gerações completas isoladas: quatro artefatos idênticos, incluindo
  registros, relógios, manifesto e marcador anterior aos sorteios.
- Uma história de verificação: 441 canais auxiliares e 764 trechos observáveis;
  168 canais sem exposição no primeiro ano não recebem história fabricada.
  As contagens são de verificação, sem inferência sobre ganho ou taxas reais.
- Seis políticas recebem os mesmos registros; seis pedidos ao armazenamento
  foram atendidos sem chamar o gerador novamente.
- O corte inicial admitiu 762 trechos; as origens posteriores admitem os 764.
  As censuras e o conjunto de registros são idênticos em fev/2024 e dez/2025.
  Sem observações avaliadas adicionais, os parâmetros ajustados nessas duas
  origens também são exatamente iguais: o histórico fechado não ganha exposição.
- A fábrica de avaliação inicializou 593 canais elegíveis na janela de 24
  meses, todos com idade zero, entrada real e fluxo 9 independente do auxiliar;
  152 entradas posteriores ao primeiro ano mantêm suas datas.
- A suíte completa passou: 155 testes, zero erros/falhas. Três testes
  suplementares, adicionados depois da descoberta da suíte, também passaram.
  Foram restaurados os metadados de replay e conferidos os 8 077 hashes
  históricos. O manuscrito não foi alterado nesta execução.

Provas: data/derived/a9/warmup_verification.json e
data/derived/a9/warmup_supplement_verification.json. Configuração e hashes em
data/derived/a9/warmup/configuration.json. Histórias volumosas de reprodução
ficam locais e podem ser regeneradas com as sementes e fontes congeladas.

## Limitações e estado restante

As idades avaliadas começam em zero no primeiro marcador observado, como em
A16; as idades reais anteriores sofrem truncamento à esquerda e não foram
reconstruídas. Nos cenários B, o ano auxiliar estacionário permanece no treino
e pode diluir ou retardar a adaptação. Não foi descartado nem reponderado.

Os registros auxiliares não entram nos desfechos, custos, MH ou testes das
políticas. A definição de aquecimento está resolvida e implementada. Ainda
faltam calibração de P1, detecção e integração/validação conjunta das seis
políticas antes das cinco réplicas completas de tempo/memória do piloto.
R permanece indefinido; não foi calculado com um piloto parcial.
