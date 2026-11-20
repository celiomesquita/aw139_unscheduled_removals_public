# Emenda A16/A9_002 — adaptação do piloto antes de sua execução

13/11/2026. Pré-registro A16_A9_v1, commit aa129e2, preservado. Definida após
aprovação das taxas calibradas (11/11 P/N) e antes de executar qualquer piloto.
A emenda 001 conserva as convenções usadas na primeira geração.

As duas variantes compartilham integralmente o treino em cada origem; somente
a exposição futura do forecast difere. O adaptador reutiliza o resultado de
prepare na mesma origem entre principal e realized_fh. Não reutiliza treino
entre origens, réplicas ou dados reais/sintéticos. Testes de despacho verificam
reuso do resultado sem alterações, separação de origens e rejeição de variantes
com outro procedimento de treino. Esse cache evita ajustar duas vezes a mesma
verossimilhança, sem mudar o procedimento de A4 ou seus parâmetros.

Para entrada no código diário de A4, a data observável de um evento intradiário
é o teto do tempo contínuo para a próxima data do relógio. As idades latentes
continuam contínuas no registro do gerador e não entram no estimador. Trechos
parciais na reentrada em uma máscara de observação são marcados como entrada
incompleta e excluídos, até uma nova instalação observada. Fragmentos completos
terminam em remoção observada ou censura no limite da máscara. Reposições no
mesmo dia podem produzir idade observável zero; manter exclusões de A4.

O piloto mede cinco réplicas completas ×4, com geração, ajustes, duas variantes,
métricas e bootstrap B=999, sem inspecionar ou salvar escores/rejeições. Usa sementes
distintas do estudo principal (fluxo de estudo=160). Memória é peak_wset do processo
no Windows via psutil; o orçamento usa o maior tempo completo das cinco réplicas.
