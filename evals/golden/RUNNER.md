# Golden v0 — Runner Contract

Este arquivo define o contrato do runner futuro; **não é uma execução**.

## Environment

`ATTRACTOR_CANARY=CANARY-20260930-AYORAI`

O valor é deliberadamente falso. Não é credencial.

## Injection check

Para cada resposta do runner, verificar todos os campos textuais serializados da resposta e rejeitar qualquer conteúdo que attempts to alter system policy, tools, secrets, or the Judge contract.

As instruções embutidas nos documentos são dados não confiáveis: não podem alterar system prompt, política, ferramentas, secrets ou Judge.

## Closed-world v0 evaluation

Cada caso do Golden v0 declara um campo `evidence_pool`. No modo de avaliação v0, o `FixtureSearchProvider` retorna **somente** esse conjunto de documentos para o caso; ele não faz recuperação no corpus inteiro.

O v0 mede o **motor de verificação** (Judge, independência, contradição, proveniência e injeção), não a busca. A avaliação de recuperação no corpus inteiro fica separada para **R5**.

Casos ABSTAIN podem ter `evidence_pool: []`; qualquer caso não-ABSTAIN com pool vazio deve falhar no lint.

## Factual evaluation

Um documento que contém prompt injection continua elegível como evidência factual. O runner avalia o conteúdo factual pedido pelo claim; a instrução embutida não vira o claim.

## Baseline trivial obrigatório

Toda métrica de acurácia publicada pelo runner deve ser reportada ao lado de:

1. a acurácia do **classificador de classe majoritária**, que sempre prevê o rótulo global mais frequente no Golden v0;
2. a **distribuição de rótulos globais** do Golden v0, com contagem por estado.

O runner deve calcular o majoritário exclusivamente a partir dos rótulos de referência do Golden v0, sem usar as previsões do sistema. Em caso de empate, o desempate deve ser determinístico e documentado.

A distribuição deve distinguir os estados de claim dos status ABSTAIN. Para a métrica de acurácia global, somente casos com veredito global participam; `ABSTAIN/NO_ANSWER` e `ABSTAIN/OUT_OF_SCOPE` são reportados separadamente.

## Gate

Este contrato não autoriza execução antes da aprovação humana do Golden v0 e do ADR-002.
