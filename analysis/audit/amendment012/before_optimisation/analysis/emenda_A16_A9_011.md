# Emenda A16/A9_011 — P1, detecção e integração temporal das políticas

14/11/2026. Posterior à verificação do aquecimento da emenda 010 e anterior
às primeiras observações avaliadas de A9/A10. Somente instâncias artificiais
foram usadas nos testes de políticas. Nenhum ganho observado foi usado para
escolher estas convenções. Protocolos e emendas anteriores preservados.

## P1: taxa esperada no calendário de visitas

Calibrar uma idade por P/N usando somente os parâmetros ajustados no histórico
auxiliar disponível antes da primeira origem e o calendário/relógio histórico
dos 365 dias anteriores. O ciclo é periódico nessa referência, sem acesso às
trajetórias avaliadas. Pesos são os números de canais sintéticos observados
nesse histórico por P/N/aeronave; não representam configuração certificada.

a9_static.py calcula uma cadeia de renovação de Markov nas fases do calendário.
O próximo evento de cada ciclo é uma remoção natural ou a primeira visita que
alcança o limiar. Integra custos e duração esperados com riscos concorrentes;
a taxa estacionária é π×custo / (π×duração). Minimiza a soma ponderada das taxas
por aeronave. Componentes independentes do limiar não alteram sua escolha.

Enumerar todos os pontos em que muda a visita elegível na discretização e
incluir o limiar infinito. Atualizações de uma linha da matriz usam a fórmula
de posto um, com refatoração periódica e conferência da estacionariedade.
Caudas têm limites explícitos de probabilidade 1e-10 e duração 1e-7 dia.
Refinar fases de um para meio e um quarto de dia; exigir concordância da taxa
mínima dentro de 1e-4 + 1e-3×|taxa|, senão registrar falha. O ótimo é global
na discretização declarada, não um certificado de ótimo no tempo contínuo.
Para β≤1, a taxa de risco não cresce com idade e a preventiva não melhora o
risco; preservar somente corretiva, sem impor idade finita.

P1 mantém sua idade e parâmetros iniciais. Na ablação P2_age, reaplicar a
mesma calibração com os parâmetros mensais, mantendo o calendário histórico
de referência congelado; não escolher um novo calendário pelo ganho observado.
P1 e P2 começam exatamente no mesmo ajuste auxiliar. Todas as MH/capacidades
são as das emendas 008 e do protocolo, iguais entre políticas.

## Wald de log η e detecção

A aproximação de Wald usa a informação conjunta de médias e efeitos log β/log η,
com componentes de variância estimados por A4 tratados como plug-in. Variância
aleatória nula compartilha a média estimada; não transforma sua incerteza em
zero. Inverter a informação somente quando definida positiva. Sem informação
válida ou ajuste, marcar detecção não avaliável, sem classificá-la como ausência
de alarme e sem excluir o custo da réplica.

Esta aproximação não propaga a incerteza da estimação dos componentes de
variância; esse limite deve acompanhar os resultados. Alarmes de parâmetro
comparam IC atual inteiro abaixo do IC inicial por P/N do rotor. Alarmes de
utilização são por aeronave: taxa observada ≥1,15×média inicial por duas
origens consecutivas. A média inicial usa o histórico auxiliar conhecido,
sem preencher utilização ausente da avaliação. O detector não recebe cenário,
instante verdadeiro de mudança, parâmetros verdadeiros ou estados latentes.

## Tempo, observações e decisões

Usar a coordenada de A16: inteiros representam o fim da data, e a idade exclui
o dia de instalação. A atualização na origem mensal ocorre ao fim do dia
anterior. A deriva começa depois do fim de 31/12/2024, antes dos incrementos
de 01/01/2025; η(t) permanece contínuo na deriva gradual e a mudança abrupta
não é interpolada para dentro do dia anterior.

As idades usadas pelas políticas derivam da instalação observável arredondada
para cima e dos relógios realizados até o corte, nunca da idade fracionária
latente. Se a instalação não é observável na máscara, não fornecer sua idade:
usar o fallback constante. O estado latente serve somente à geração e aos
desfechos físicos do simulador. Custos incluem todos os eventos dentro dos
limites dos canais, inclusive os não observáveis ao estimador.

Visitas ocorrem após eventos naturais da data. O plano mensal de P2/P2_fixed/P3
executa suas preventivas nas visitas até a atualização seguinte, mesmo que
tenha ocorrido uma renovação natural; o custo integrado das sequências já
inclui essa possibilidade. P1/P2_age comparam o limiar à idade projetada no
relógio congelado na atualização, relocalizando a próxima visita após uma
renovação observada. O eixo conhecido usa o caminho exógeno futuro; o previsto
usa somente a taxa dos 90 dias passados corrigida. A idade/parametrização de
P1 não é reotimizada com resultados de avaliação. Conflitos nas políticas
de idade priorizam custo esperado evitado por MH, com desempate P/N e canal.

P3 conhece parâmetros verdadeiros vigentes na decisão, sem antecipar mudanças
futuras de η ou conhecer limiares de eventos. Compartilha o horizonte, relógio
do eixo informacional, observabilidade de idade e conjunto factível das demais.
As visitas no último dia do horizonte são admissíveis; o arco final pode ter
duração zero após essa preventiva. Unidades censuradas antes do horizonte não
recebem preventivas posteriores à sua censura.

Depois de dez/2025, relógios e visitas da extensão são repetidos a partir do
primeiro ano, período de 366 dias. Essa extensão é sintética; não usa os registros
reais de jan–mar/2026 nem entra nos desfechos. Na previsão principal, a taxa
permanece congelada inclusive na extensão terminal, sem recalculá-la no futuro.

## Quadratura terminal

Além do limite de cauda da emenda 009, comparar ordens 8, 16, 32, 64 e 128
de Gauss–Legendre e exigir diferença ≤1e-8×(1+|custo|) em todas as idades.
Transformar o primeiro incremento positivo quando idade zero produzir
singularidade. Registrar separadamente diferença de quadratura e limite de
truncamento; falha em qualquer um bloqueia o custo, sem trocar tolerância
pelo desempenho da política. A versão anterior do integrador fica arquivada
em analysis/audit/amendment009/a9_renewal.py; a versão anterior do adaptador
de ajuste está em analysis/audit/amendment010/a9_fitting.py.

## Piloto e sementes

Fixar cinco réplicas completas na célula ampliada, utilização conhecida, r=10,
B-gradual (índice 71 na ordem nível=[calibrated,null,amplified], conhecimento,
r e cenário). É uma escolha anterior aos custos, não garantia de maior runtime
de toda a grade. Cada medição inclui geração auxiliar, ajuste inicial, calibração
P1 e as seis políticas; não usar tempos de um subconjunto para fixar R.
Não abrir tabelas de ganho/alarme do piloto; descartá-las após medir tempo,
memória, falhas e completude. Não iniciar a execução principal automaticamente.

A avaliação usa fluxo 9, fase, célula, nível, réplica, P/N, aeronave, canal,
renovação e risco, sem índice de política. O aquecimento mantém seu fluxo 90
independente e compartilhado por nível/réplica, como na emenda 010. O orçamento
de A9/A10 permanece 120 h; se a fórmula das 72 células não comportar R≥200,
parar e informar o autor, sem reduzir a grade ou substituir o piloto por previsão.
