# AYORAI ATTRACTOR — Progress

**Estado atual:** Fase 0 concluída; R1 core implementado na main; integração do R1 com o Golden v0 e recuperação real continuam sendo trabalho posterior.
**Base:** main merge 04d6e25b5f264fe876709e810260af7d132d2836.
**Ground Truth:** 34 casos / 52 documentos.
**Baseline:** 43,3333%, igual à classe majoritária.

## Roadmap ponderado

| Item | Peso | Status | PRs |
|---|---:|---|---|
| Fase 0 — Fundação e ground truth | 10 | concluído | #7–#14 |
| R1 — Motor de verificação | 15 | core concluído; integração Golden pendente | #27–#31 |
| R2 — Audit Mode | 10 | não iniciado | — |
| R3 — Conselho de IAs | 10 | não iniciado | — |
| R4 — Proveniência e replay | 6 | não iniciado | — |
| R5 — Recuperação híbrida OpenSearch | 8 | não iniciado | — |
| R6 — Síntese fiel por construção | 6 | não iniciado | — |
| R7 — Segurança (MCP, OWASP ASI, red team) | 8 | não iniciado | — |
| R8 — Observabilidade e custo | 5 | não iniciado | — |
| R9 — Orquestração multi-agente durável | 7 | não iniciado | — |
| R10 — Arena comparativa | 5 | não iniciado | — |
| R11 — Aprendizado GEPA | 3 | não iniciado | — |
| R12 — Attractor Studio + MCP próprio | 5 | não iniciado | — |
| R13 — Escala, operação e governança | 2 | não iniciado | — |

## Progresso ponderado

**25/100 = 25%** do roadmap ponderado tem implementação concluída ou core tecnicamente implementado.

- Fase 0: 10/10
- R1 core: 15/15
- R2–R13: 0/75

Isso não significa 25% de um produto pronto: R1 ainda precisa ser ligado ao fluxo de avaliação Golden e a recuperação real só entra em R5.

## R1 entregue

- contratos Pydantic estritos;
- independência determinística e clusters transitivos;
- parser numérico por locale;
- tolerância relativa de 1% e limiar de 1e-9;
- conflito por granularidade de data;
- Judge determinístico de seis estados;
- precedência global;
- completude de proveniência explícita;
- contratos ABSTAIN/NO_ANSWER e ABSTAIN/OUT_OF_SCOPE;
- scanner recursivo de segredo de avaliação;
- testes unitários e property tests.

## Próximos marcos

1. Integrar o Judge ao runner Golden v0 e cobrir os 34 casos.
2. Fechar R2 com Audit Mode e trilha de decisão/replay.
3. R3: conselho multi-modelo controlado.
4. R4/R5: proveniência/replay e recuperação híbrida real.

## Histórico

- PR #31: R1 core integrado na main.
- PR #29 e #30: branches intermediárias fechadas após a integração consolidada no #31.
- Master Gate: concluído em 2026-09-30.