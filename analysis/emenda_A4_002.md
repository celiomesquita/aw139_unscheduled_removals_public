# Emenda A4_002 — gradiente do objetivo marginal de Laplace

Data: 12/11/2026. Decisão após a primeira origem de treino da tentativa real,
antes de qualquer decisão K2-A4/K2-idade ou inspeção de seus escores. A tentativa
foi interrompida e será reiniciada integralmente; não há resultado final retido.
O protocolo e a emenda 001 permanecem preservados.

Problema: diferenças finitas externas recalculam todos os modos condicionais
para cada coordenada dos hiperparâmetros. Isso torna custosa a execução completa
das origens e sensibilidades, sem alterar o problema científico investigado.

Alteração: usar o gradiente do MESMO objetivo de Laplace. Diferenciação implícita
do modo condicional usa a inversa da Hessiana posterior; a derivada de log det H
usa 0,5 tr(H^-1 dH). Derivadas terceiras da verossimilhança são obtidas por
diferenças centrais de suas Hessianas analíticas, passo fixo 1e-4 em log parâmetro.
Variâncias exatamente zero continuam reduzindo a dimensão, com tratamento das
coordenadas fixas. O objetivo, famílias, escalas, inícios, limites, orçamento,
critérios, dados e sensibilidades não mudam.

Validação antes da nova execução: comparar esse gradiente com diferenças finitas
do objetivo marginal em dados simulados; repetir testes de recuperação e limites.
Falha nessa comparação impede o uso do gradiente na análise real. Não é uma
mudança de modelo ou seleção orientada por um resultado favorável.
