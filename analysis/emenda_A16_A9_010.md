# Emenda A16/A9_010 — coorte auxiliar de aquecimento comum às políticas

14/11/2026. Autorização explícita do autor, posterior às emendas 008–009 e
anterior à geração de qualquer observação auxiliar ou de política da frota.
O pré-registro e as emendas anteriores são preservados. Esta emenda resolve
a definição de aquecimento pendente na emenda 009, sem reabrir A16.

## Coorte auxiliar e separação da avaliação

Usar os canais, limites de observação e relógios do primeiro ano, jan–dez/2024,
deslocados **exatamente 365 dias** para trás. Não substituir por deslocamento
de ano civil. Preservar as entradas tardias e as máscaras de observação;
um canal que não entra nesse primeiro ano não recebe história auxiliar.
Não gerar idade anterior à primeira instalação observada do canal.

O processo auxiliar é estacionário, com o nível de β da réplica e a regra
pré-especificada de preservação de vida média para η. Intensidades concorrentes
permanecem as originais congeladas. A política auxiliar é sempre P0, sem
preventivas, para todas as políticas e ablações.

Nenhuma unidade auxiliar continua na avaliação. Os canais avaliados mantêm
as entradas reais com idade zero, exatamente como em A16. Identificadores
de coorte/unidade e suportes de relógio são distintos, sem somar dois relógios
no mesmo par aeronave/data nem fornecer idade auxiliar a uma unidade avaliada.
O relógio auxiliar serve às idades dos seus próprios registros; não preenche
história de utilização ausente da aeronave na avaliação.

Como 2024 é bissexto, o deslocamento de 365 dias pode colocar a extremidade
final auxiliar em 01/01/2024. Não antecipar essa observação para o ajuste
inicial: a regra de corte exclusivo continua válida. Registros ainda censurados
na primeira origem usam somente o passado disponível; depois de encerrada a
observação auxiliar, sua censura fica congelada, sem aumentar exposição nas
origens posteriores. A sobreposição de datas não mistura as duas coortes.

## Uma geração por réplica, fluxo próprio e números aleatórios comuns

Gerar o aquecimento uma única vez por réplica, com sementes independentes
das unidades avaliadas e fluxo próprio **90**. A chave inteira é
[20261112,90,fase,nível_β,réplica,P/N,aeronave,canal,renovação,risco].
Fases distintas: verificação=0, piloto=1 e principal=2. Riscos 1 e 2 usam
fluxos independentes. Não usar hash() de Python.

O aquecimento não depende de r, conhecimento da utilização, cenário A/B,
política ou ablação. Para o mesmo nível de β, fase e índice de réplica,
reutilizar a mesma realização nas células que diferem somente nesses eixos.
P0–P3 e as duas ablações recebem cópias idênticas do mesmo histórico; nenhuma
política volta a sortear ou modifica o aquecimento compartilhado.
O compartilhamento entre células não constitui novas réplicas independentes.

Salvar configuração e hashes antes dos sorteios, preservar resultados
existentes na retomada e conferir hashes antes de reutilizar o histórico.
Alteração da configuração ou de entradas exige identificação própria, sem
sobrescrever uma réplica já gerada. Reproduções para verificação não aumentam R.

## Uso em todas as origens e censura

Os registros auxiliares entram como histórico passado em **todas** as origens,
pela regra de treino pré-registrada. Não são descartados após o primeiro ajuste.
Suas datas de encerramento e censura permanecem fixas. Não contam como saídas
concorrentes, preventivas ou unidades em risco depois do fim da observação.

Não avaliar registros auxiliares: excluir de custos, eventos, MH, denominadores
e desfechos das políticas, testes H3a/H3b, detecção avaliada e ablações. Eles
podem influenciar os parâmetros estimados e os valores iniciais de referência,
pois esse é o propósito do histórico de ajuste. A independência das sementes
não é validação externa; todos os registros são sintéticos e condicionais ao
gerador derivado de A4 original.

## Limitações obrigatórias

As idades das unidades avaliadas começam em zero no primeiro marcador
observado, como em A16: as idades reais anteriores sofrem truncamento à esquerda
e não são reconstruídas. Isso restringe a interpretação do mapa de condições
de ganho e não representa renovação física demonstrada na frota real.

Nos cenários B, o ano auxiliar estacionário permanece no treino em todas
as origens. Ele pode diluir ou retardar a reestimação após a deriva. Não
descartá-lo, reduzir seu peso nem mudar a janela de treino para melhorar P2.
Esse efeito faz parte do desenho e deve acompanhar os resultados de detecção,
ganho e ausência de ganho.

## Verificação e estado

Antes do piloto, verificar deslocamento exato de 365 dias, sementes/coortes
independentes, entradas tardias, idade inicial zero na avaliação, igualdade
integral do histórico entre as seis políticas e permanência do histórico nas
origens posteriores à deriva. Conferir censuras fixas, ausência de inclusão
auxiliar nos desfechos e determinismo em duas gerações completas isoladas.
Não alterar a grade, o orçamento de 120 h nem calcular R com um piloto parcial.
Esta emenda não afirma que o simulador completo ou o piloto estejam prontos.
