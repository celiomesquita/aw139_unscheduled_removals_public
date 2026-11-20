# Emenda A16/A9_009 — integração numérica e observações sob políticas

14/11/2026. Posterior à emenda 008 e à autorização de prosseguir, anterior
a qualquer réplica de políticas da frota ou piloto A9/A10. Esta etapa usa
somente instâncias artificiais de parâmetros conhecidos. Os protocolos
originais e as emendas anteriores permanecem intactos.

## Renovação e custo terminal

a9_renewal.py integra a equação de renovação, não uma soma de probabilidades
marginais. Após cada evento, o valor de continuação começa com idade zero.
Os pesos de integração interpolam linearmente a continuação entre pontos da
malha; o termo no próprio ponto é resolvido algebricamente. Isso permite
múltiplas renovações por intervalo e não limita eventos a um por dia.

As incidências dos riscos são integradas nas respectivas coordenadas de
probabilidade, com transformação de potência no nascimento para tratar a
singularidade de Weibull com β<1. Gauss–Legendre integra os pesos, e o erro
de massa é conferido contra a sobrevivência total conhecida. Malhas dividem
os dias em 1, 2, 4, 8, 16, 32 ou 64 partes, sem alterar os relógios diários.

a9_planning.py refina todos os custos de arcos, e não somente o custo do plano
selecionado. Aceitação: diferença entre malhas sucessivas ≤0,001 + 1e-4×|custo|
para cada arco e erro de massa <1e-7. Ausência de convergência no limite da
malha é falha numérica explícita, sem aceitar um plano mais favorável.

O custo terminal é o custo esperado do primeiro evento natural após o fim do
horizonte, condicionado à idade da unidade então em serviço e à sobrevivência.
Não adiciona ciclos posteriores nem contabiliza eventos dessa extensão nos
desfechos. Há riscos concorrentes de custo unitário e não programado de custo r.
Para o relógio periódico fornecido ao integrador, a extensão termina quando a
probabilidade residual multiplicada pelo maior custo é ≤1e-9. Essa é uma
barreira de truncamento, distinta do erro de quadratura. A validação final deve
conferir ambos antes de instanciar as políticas da frota.

## MILP equivalente por caminhos

a9_arcflow.py representa todas as sequências admissíveis por caminhos num
grafo acíclico: fonte, visitas ordenadas e destino. O custo de um arco é o
custo de renovação desde a última preventiva até a próxima, mais a preventiva
no destino se houver. No último arco entra o custo terminal. Depois de uma
preventiva, idade zero torna o custo do próximo trecho independente do trecho
anterior, para parâmetros/relógio congelados na decisão.

Cada unidade recebe um fluxo binário unitário da fonte ao destino. A capacidade
de uma visita conta as MH dos arcos que nela entram. Assim, cada caminho
corresponde a uma coluna de sequência, e cada coluna a um caminho, com os
mesmos custo e incidências de capacidade. Não há poda de sequências, limite
artificial de preventivas ou horizonte menor para reduzir o MILP. A equivalência
foi testada contra a formulação explícita e a enumeração completa em instância
pequena. Permanecem CBC, thread única, semente 20261112, gap 1e-6, limite
300 s e o fallback determinístico previsto no protocolo.

## Estado latente e registro observável

a9_events.py mantém idade e limiares residuais dos dois riscos ao mudar η ou
utilização. Na deriva gradual, integra o risco com η(t); não sorteia nova vida
no ponto de mudança. Cada renovação usa chave inteira própria e dois riscos
independentes; a chave de outro canal não é afetada por uma preventiva.
Eventos concorrentes precedem empates e preventivas ocorrem depois dos eventos
naturais daquele instante. Não existe teto de um evento por dia.

a9_fitting.py arredonda início/fim para a data superior, como A16, e não envia
idades fracionárias latentes ao ajuste. O suporte temporal do relógio pode
abranger o aquecimento, mas a verossimilhança, famílias e limites de A4 são
reutilizados. Cortes de treino continuam exclusivos.

Uma preventiva da política censura a vida sem contar como remoção não
programada. Para a intensidade de risco concorrente exógeno, seu indicador é
excluído do numerador: a intensidade usa apenas saídas exógenas observáveis.
Seu tempo até censura permanece no denominador e no ajuste de sobrevivência.
Isso impede que o estimador trate ações de P2 como aumento do risco concorrente
natural. Os diagnósticos de referência identificam explicitamente essa regra.

## Aquecimento — definição pendente, sem execução dependente

A seção 3 manda preservar primeiras instalações; a seção 6 requer histórico
sintético de 12 meses anterior à avaliação e explicita entradas tardias. A
extensão deve definir como os canais de aquecimento se relacionam aos canais
avaliados, sem criar idade histórica não observada ou uma renovação imposta.

Foi enviada ao autor a escolha entre:

1. Coorte auxiliar sintética com relógios/canais do primeiro ano deslocados ao
   ano anterior, somente para ajuste inicial; entradas e idade inicial zero
   dos canais avaliados permanecem nas datas reais.
2. Continuidade dos mesmos canais entre aquecimento e avaliação, com definição
   explícita das entradas por emenda.

Nenhuma opção foi presumida por silêncio. A versão executável e o manifesto
do piloto registrarão a definição recebida antes de gerar essas observações.
Ainda faltam validação conjunta das seis políticas, calibração da idade P1,
detecção, interpretação operacional dos relógios e da extensão terminal.
Os módulos numéricos isolados não certificam prontidão de A9/A10.
