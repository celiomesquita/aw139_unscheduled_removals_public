# Emenda A16/A9_003 — revisão de orçamento de A16 (decisão do autor)

13/11/2026. Pré-registro A16_A9_v1, commit aa129e2, e emendas 001 e 002 preservados.

## Momento e conhecimento disponível

Decidida após a aprovação do gerador calibrado (11/11 P/N) e após o piloto de
tempo de A16, que mediu somente tempo e memória. Nenhuma métrica, rejeição,
estimativa de poder ou erro tipo I foi calculada ou inspecionada. A9/A10 não
foram iniciadas nem pilotadas.

## Motivo

A regra da seção 5 parou T12: com o maior tempo do piloto (76,688 s por réplica
completa, duas variantes, B = 999) e reserva de 1,5, R = 200 nas nove células exige
57,52 h, acima das 48 h reservadas a A16. A regra dá R = 150, abaixo do mínimo.

## Alteração

- T_disponível de A16 passa de 48 h para **60 h**.
- T_disponível de A9/A10 permanece **120 h**. O orçamento total de T12 passa de
  168 h para **180 h**. Não há transferência de horas de A9/A10 para A16.
- A fórmula, o fator 1,5, o uso do maior tempo do piloto, o mínimo de 200 e o
  máximo de 1 000 réplicas ficam inalterados. Com 60 h:
  R = 50 × floor(216 000 / (9 × 1,5 × 76,688) / 50) = 50 × floor(4,17) = **200**.
- Grade, variantes, B, sementes, critérios e interpretação de A16 não mudam.

## Consequência inferencial

Nenhuma: a alteração é de recurso computacional, decidida sem acesso a resultados,
e mantém o R mínimo pré-registrado. Se o tempo real exceder 60 h, a execução não é
interrompida por significância nem por resultados parciais; o excedente é registrado.
Se o piloto de A9/A10 indicar R < 200 com 120 h, a regra de parada de A9 se aplica
e uma nova decisão do autor será necessária.
