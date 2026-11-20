# Emenda A16/A9_001 — convenções de implementação anteriores à geração

13/11/2026. Referência: pré-registro A16_A9_v1 commitado em aa129e2, incluindo
as três alterações do autor anteriores ao commit. O pré-registro é preservado.
Nenhuma réplica com dados da frota foi gerada ao definir estas convenções.

## Calendário, relógios e posições

A primeira barreira usa somente o gerador estacionário; não implementa políticas,
ajustes A16 ou cenários de deriva antes de conhecer sua validade. A janela termina
em 31/03/2026, conforme A4. A curva de FH usa Exposure de A5/A4 e interpolação
linear entre valores acumulados nas datas: idade na instalação é zero; o incremento
do dia da instalação é excluído como em Exposure. Decolagens e máscaras de
ausência são preservadas no artefato diário, sem nova imputação. A escala principal
continua FH/calendário; decolagens não são um eixo adicional nesta barreira.

Coloração dos intervalos reais, dentro de cada aeronave/P/N, usa intervalos
semiabertos [instalação,remoção), ordenados por instalação, remoção e índice estável
da linha de spells.csv. Reusar o menor canal cujo último fim seja ≤ nova instalação.
Trechos de duração zero conservam seus marcos, mas não criam exposição ou eventos
válidos, como as exclusões por idade zero de A4. Intervalos negativos são erro.
Nenhum número de série ou texto livre é exportado. A tabela de marcos preserva
todas as datas reais e o vínculo ao canal sintético, sem renovar sua idade latente.

Cada canal começa na primeira instalação observada e termina no último limite
de observação desse canal (no máximo o fim da janela). A união dos seus intervalos
reais define a máscara de observação. Durante lacunas, a unidade latente continua
e pode renovar; eventos/exposição fora da máscara não entram nas taxas observáveis.
Fronteiras adjacentes não implicam renovação imposta. Na reentrada, o registro
observável deve indicar idade incompleta; não fornecer a idade latente ao ajuste.
Essa convenção explicita a distinção prevista entre instalação real, estado latente
e registro observável. Não representa identificação de posições físicas.

## Taxas e distribuições

O denominador real é a soma de exposição dos trechos principais de A4, na escala
fixada por P/N, com exposição positiva, calculada por Exposure; o numerador exclui
eventos com exposição zero como o ajuste A4. O denominador sintético corresponde
à mesma máscara real, sem multiplicar o período observado pelo número de renovações.
Se uma remoção sintética tiver idade operacional zero, registrá-la separadamente
e aplicar a mesma exclusão de evento do ajuste. Competing_rate diária é a última
estimativa da variante principal, modelo w e escala fixada.

Gerar 1 000 réplicas em cada nível de β; a regra média-preservada de η é exatamente
a do autor. O nível calibrado governa a parada. Os dois outros níveis são
descritivos, como prevê a seção 4. Quantis preditivos usam numpy.quantile, método
linear, α=0,05/11. A incerteza Monte Carlo da média da taxa é desvio entre réplicas
dividido por √1000; reportar também a dispersão preditiva.

As ECDF e quantis de idade agregam eventos observáveis de cada nível, mantendo
as distribuições reais em separado. Guardar registros latentes de renovação,
censuras finais, marcos de observação e contagens por réplica. Idades reais usam
o relógio A4; idades sintéticas usam o mesmo relógio interpolado. Comparar Wasserstein
em amostra agregada e normalizar pela mediana real se positiva. São diagnósticos,
não critérios adicionais de aprovação ou motivos de recalibração.

## Aleatoriedade e testes anteriores à barreira

SeedSequence(20261112), chaves inteiras (estudo=16, nível, réplica, índice ordenado
do P/N, código AC, canal, risco). Fluxos independentes para os dois riscos; um
limiar por risco em toda renovação, inclusive quando o outro risco vence.
Não usar hash() de Python. Testes de inversão, memória após renovação, censura,
relógio zero, entrada tardia, eventos intradiários múltiplos, canal e preservação
de média antecedem a geração real. Validação de quantis teóricos usa bandas
binomiais de 99% definidas por n e probabilidade, sem ajustar tolerâncias aos dados.

Nenhuma modificação metodológica de A4/A5 foi realizada. Se a barreira falhar,
parar após documentar os resultados, sem piloto, ajustes de poder ou otimização.
