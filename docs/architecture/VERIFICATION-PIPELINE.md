# Pipeline de verificação composta (biblioteca)

Para a visão geral atual dos limites entre API, CLI e biblioteca, consulte o [Manual Técnico — capítulo 02: Arquitetura](../manual/02-arquitetura.md).

## Composição implementada

`src/ayorai_attractor/verification/pipeline.py` compõe três operações: chama o Judge r1-a com afirmações, evidências e relações de stance já estruturadas; monta as referências de evidência por afirmação; e chama `GroundedSynthesizer` em `src/ayorai_attractor/synthesis.py` para verificar se as afirmações de saída têm IDs de evidência conhecidos. Se o gate de grounding falha, a síntese devolve uma resposta explícita de abstenção.

Esse é um pipeline de biblioteca, testado separadamente. Ele não é importado diretamente por `src/ayorai_attractor/api/app.py` nem por `src/ayorai_attractor/cli/main.py`. A rota pública `POST /v1/verify` usa os caminhos de Judge r1-a e Judge 2 r2-a definidos em `api/app.py`; não chama `verification/pipeline.py`.

## Não confundir com o pipeline de avaliação

`src/ayorai_attractor/verification/claim_pipeline.py` é um módulo distinto. A avaliação Golden em `src/ayorai_attractor/evaluation/golden.py` importa e usa esse pipeline de afirmações. Essa ligação não torna `verification/pipeline.py` parte do caminho da API nem da CLI `search`.

## Evidências e limites

- Implementação composta: `src/ayorai_attractor/verification/pipeline.py`.
- Gate de grounding: `src/ayorai_attractor/synthesis.py`.
- Pipeline usado na avaliação Golden: `src/ayorai_attractor/verification/claim_pipeline.py` e `src/ayorai_attractor/evaluation/golden.py`.
- Entry points de serviço: `src/ayorai_attractor/api/app.py` e `src/ayorai_attractor/cli/main.py`.

A existência e os testes dessa biblioteca não demonstram que ela esteja integrada à API pública, nem que faça extração de afirmações ou inferência de stance automaticamente no contrato `POST /v1/verify`.
