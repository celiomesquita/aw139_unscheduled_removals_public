# Emenda A16/A9_006 — correção da exposição prevista com histórico parcial

**Versão para commit do autor, 13/11/2026. T14 concluída antes de T15/T16.**
Pré-registros A5, A4 e A16/A9 e emendas 001–005 preservados. Esta emenda é
posterior ao conhecimento de A5/A4, dos 600 controles antigos e do diagnóstico
exploratório T13. Nenhum resultado corrigido em dados reais ou controle novo
foi produzido para escolher esta regra. Os testes da correção usam dados sintéticos.

## 1. Defeito e decisão do autor

Exposure.rates, em analysis/a5_models.py, divide sempre por 90. Na entrada
tardia, a janela contém dias anteriores ao primeiro registro e o código trata
o histórico parcial como suficiente para a projeção. A tarefa da rodada 5
identificou isso como desvio de implementação do fallback previsto, não mudança
de desenho. T13 documenta o mecanismo e a contribuição de AC-22/2025-12-01.

A5/A4 originais, seus artefatos, relatórios, decisões e pré-registros continuam
como executados. A análise corrigida será uma errata identificada separadamente.
Os 600 controles antigos de A16 ficam preservados e reportados como invalidados
pelo defeito para a finalidade de calibrar a regra corrigida. A exclusão
diagnóstica de T13 não substitui esses controles nem modifica sua barreira.

## 2. Regra fixada antes dos resultados corrigidos

Seja t0 a origem de previsão (o **corte**, exclusivo, nesta emenda). O último
dia acessível ao treino é t0−1. A janela é [t0−90 dias,t0), igual à janela do
numerador original: cumulativa(t0−1)−cumulativa(t0−91).

O primeiro registro é a primeira linha datada da aeronave em hours_flown.csv,
com qualquer valor de FH/decolagens, inclusive zero ou ausente. Dias observados:

`D = max(0, min(90, t0 − max(t0−90, primeiro_registro)))`, em dias calendário.

Não contar somente dias com voo, dias com linha ou dias de utilização positiva.
Os dias a partir do primeiro registro dentro da janela contam no denominador.
Não usar registros posteriores ao corte para estimar a taxa ou imputar ciclos.
Antes do primeiro registro, D=0, sem informação disponível.

Para FH e decolagens, quando D≥30, usar o incremento acumulado da escala na
janela original dividido por D. Manter as regras originais de ausência de
decolagens, casos completos e imputação por razão decolagens/FH calculada no treino.
Quando D<30, a exposição prevista é **indisponível**, não zero ou taxa inventada.

### Fallback obrigatório

- A5: usar a previsão em calendário do próprio modelo e seus fallbacks existentes,
  com marcador explícito; não inventar um ajuste calendário se ele não convergiu.
- A4/A16: usar a base constante (c), igual para h-W e h-E, com marcador explícito.
- Aplicar aos modelos em FH e decolagens; modelos selecionados em calendário
  não recebem uma substituição por ausência de informação de voo.
- Dias com voo zero registrado continuam sendo zero; histórico suficiente com
  taxa observada zero não é classificado como histórico ausente.

Marcadores do adaptador: observed_days_90d, exposure_available_90d,
exposure_min_days e motivos calendar_observed_days_lt_30 ou
baseline_observed_days_lt_30 nos campos de fallback. Para sensibilidade, os
motivos usam o limiar 60. Esses marcadores descrevem disponibilidade da
projeção operacional, não ausência de idade calendário.

### Sensibilidade única

Repetir com limiar D≥60, fixado agora. Não testar outros limiares nem escolher
30/60 pelo desempenho. O principal permanece 30 dias.

### Saída da aeronave e FH realizadas

O inventário T13 lista também horizontes posteriores ao último registro, sem
corrigi-los. Esta emenda não inventa data de saída, não trunca D no último voo
e não modifica os limites da janela de dados ou a elegibilidade. Permanecem os
fallbacks existentes quando não há informação de utilização no treino.

A variante realized_fh é controle com exposição realizada e deve reproduzir
integralmente os resultados originais, inclusive colunas e marcadores. O
adaptador usa o fluxo original nessa variante, sem aplicar a nova regra de
exposição prevista. Nenhum outro elemento dos protocolos muda.

## 3. Independência dos modos de A4 e do gerador

Verificação anterior a T15/T16 em analysis/check_exposure_independence.py e
data/derived/a16/exposure_independence.json:

- training_view, Evaluation.prepare, HierarchicalEvaluation.prepare e os
  métodos de relógio/idade usados no treino não chamam Exposure.rates;
- efeitos e diagnósticos de treino salvos de A4, principal e realized_fh, são
  exatamente iguais em todas as origens, incluindo os 11 modos condicionais
  h-W na origem 2025-12-01;
- load_design do gerador funciona mesmo com Exposure.rates bloqueado por erro;
  parâmetros verdadeiros e taxas/exposições observadas reproduzem exatamente
  os CSV usados na validação original;
- todos os artefatos da validação do gerador mantêm seus hashes.

Assim, os modos e a validação de taxas/idades não dependem da exposição prevista;
continuam válidos e não serão recalibrados. Nenhum modelo real foi reajustado
nessa verificação. Se nova evidência contrariar essa independência, parar e
informar o autor antes de prosseguir.

## 4. Execuções posteriores ao commit

T15 produz a errata real em data/derived/a5_errata/ e a4_errata/, preservando
integralmente as pastas, relatórios e pré-registros originais. Mesmas sementes,
B=10 000 e sensibilidades previstas; apenas a correção desta emenda e a
sensibilidade 60 dias são novas. Reportar original × corrigido, agregado e
por P/N, com contagens afetadas. Uma decisão corrigida diferente não apaga
a decisão original. Não usar a errata para alterar o gerador ou os desenhos
de A16/A9. O teste que reexecuta A5 é autorizado em T15, não nesta etapa.

T16 usa fluxo **17** em vez de 16. Manter o restante da estrutura da chave
da emenda 004, R=200, B=999, grade, variantes e multicore validado na emenda
005. Não recalcular R com o novo tempo. Os controles antigos não entram em
estimativas novas. Executar primeiro β=1 ×1/×2/×4, ambas as variantes.
Se erro tipo I agregado ou familiar >0,10 em célula completa, ou controle não
avaliável, parar e informar, sem outra correção. Se passarem, executar as seis
células de efeito e a interpretação já fixada. Só depois iniciar piloto A9/A10.

A9 aplica a regra corrigida à projeção de utilização de 90 dias de P2 desde
o início, não somente após detectar deriva. A sensibilidade 60 dias permanece
identificada separadamente; não escolher o limiar que gere economia.

## 5. Orçamento e rastreabilidade

A16 permanece com 60 h, A9/A10 com 120 h. O tempo já consumido não é zerado:
preservar tempos do piloto, execução sequencial, multicore e controles antigos,
registrando separadamente tempo de parede e soma de tempos de processos quando
disponíveis. Indicar lacunas de medição, sem inventar duração para registros
ausentes. Somar a nova rodada ao histórico. Se as 60 h forem excedidas,
registrar o excedente sem parada por significância, conforme emenda 003.

O adaptador em analysis/exposure_errata.py é separado dos códigos originais.
Nesta etapa foi exercitado somente com casos sintéticos. Os hashes de A5/A4,
pré-registros, relatórios, emendas anteriores e controles antigos devem ser
conferidos antes e depois das execuções futuras. Arquivos editoriais externos
do manuscrito permanecem fora da intervenção do Codex, como na emenda 005.

## 6. Testes e parada atual

Testes sintéticos verificam entrada tardia, primeiro registro com qualquer valor,
30/60 dias, saída e voo zero, taxas FH/decolagens, igualdade do fallback h-W/h-E
em A4/A16, fallback calendário em A5, igualdade exata das previsões originais
quando todas as janelas são completas e igualdade integral da variante
realized_fh mesmo sob entrada tardia. T13 verifica agregação/contribuições e
exclusão somente de AC-22/2025-12-01 e suas cópias. Duas execuções completas do
diagnóstico devem reproduzir as saídas; nenhuma rodada corrigida é realizada.

**Parar e solicitar o commit desta emenda ao autor antes de T15 e T16.**
