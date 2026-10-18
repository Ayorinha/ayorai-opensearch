# Arquitetura

A referência atual para os limites verificados entre serviço e biblioteca é o [Manual Técnico — capítulo 02: Arquitetura](manual/02-arquitetura.md). Este arquivo funciona como resumo de navegação; descrições conceituais antigas não devem ser lidas como componentes integrados sem confirmação no código.

## Caminhos atuais

- A API está definida em `src/ayorai_attractor/api/app.py`. As rotas operacionais usam `Attractor`; `POST /v1/verify` despacha os contratos r1-a e r2-a para seus caminhos de Judge.
- A CLI está definida em `src/ayorai_attractor/cli/main.py`. O comando `search` chama `Attractor.run()`; o comando `eval` chama `evaluate_golden_v0()`.
- `src/ayorai_attractor/orchestrator.py` seleciona cinco classes concretas em `IMPLEMENTED_AGENTS`.
- `src/ayorai_attractor/agents/roles.py` declara 26 itens de metadados em `INITIAL_ROLES`; eles não equivalem a 26 implementações de agentes.

## Limites de integração

`verification/claim_pipeline.py` é usado pela avaliação Golden. `verification/pipeline.py` e `synthesis.py` formam outro pipeline de biblioteca e não são importados diretamente pelos entrypoints da API ou da CLI. Os detalhes e a lista de módulos confirmados fora desses caminhos estão no [capítulo 02](manual/02-arquitetura.md).

## Fontes de verdade

- `src/ayorai_attractor/api/app.py`
- `src/ayorai_attractor/cli/main.py`
- `src/ayorai_attractor/orchestrator.py`
- `src/ayorai_attractor/agents/core.py`
- `src/ayorai_attractor/agents/roles.py`
- `src/ayorai_attractor/evaluation/golden.py`
