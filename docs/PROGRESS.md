# AYORAI ATTRACTOR — Progress

**Estado atual:** Fase 0 concluída; R1 core implementado; núcleos determinísticos de R2, R3, R4, R5, R6, R8, R9, R10 e R13 adicionados. As integrações operacionais completas e R11 ainda permanecem.
**Base:** main merge 13621913af657708867021f8442bf6919fc6aa3f.
**Ground Truth:** 34 casos / 52 documentos.
**Baseline:** 43,3333%, igual à classe majoritária.

## Roadmap ponderado

| Item | Peso | Status | PRs |
|---|---:|---|---|
| Fase 0 — Fundação e ground truth | 10 | concluído | #7–#14 |
| R1 — Motor de verificação | 15 | core concluído; Golden integration pendente | #27–#31 |
| R2 — Audit Mode | 10 | core concluído; exposição operacional pendente | #32 |
| R3 — Conselho de IAs | 10 | core concluído; adapters/orquestração pendentes | #33 |
| R4 — Proveniência e replay | 6 | core concluído; persistência/integração pendentes | #33 |
| R5 — Recuperação híbrida OpenSearch | 8 | core de fusão concluído; pipeline real pendente | #34 |
| R6 — Síntese fiel por construção | 6 | grounding gate concluído; integração de geração pendente | #34 |
| R7 — Segurança | 8 | parcialmente implementado; red team/OWASP pendentes | #27–#31 |
| R8 — Observabilidade e custo | 5 | métricas core concluídas; telemetria integrada pendente | #34 |
| R9 — Orquestração durável | 7 | checkpoint core concluído; execução distribuída pendente | #35 |
| R10 — Arena comparativa | 5 | scoring core concluído; harness completo pendente | #34 |
| R11 — Aprendizado GEPA | 3 | não iniciado | — |
| R12 — Attractor Studio + MCP próprio | 5 | infraestrutura existente; produto MCP dedicado pendente | — |
| R13 — Escala, operação e governança | 2 | checks de governança core concluídos; operação pendente | #34 |

## Progresso honesto

**25/100 = 25%** do roadmap ponderado é contado como fase/core suficientemente implementado para não ser apenas documentação. Os módulos adicionais acima são fundações parciais e não são contados como fases 100% concluídas.

## Próximo gargalo técnico

1. Integrar R1 ao runner Golden v0 e reavaliar os 34 casos.
2. Expor R2 Audit Mode no fluxo/API.
3. Ligar R3/R4 ao orchestrator e ao armazenamento de traces.
4. Integrar R5 ao adaptador OpenSearch e R6 ao pipeline de resposta.
5. Implementar R7 red team, R11 GEPA e R12 MCP dedicado.

Não há uma alegação de conclusão total enquanto esses itens não estiverem executáveis e testados.

## CI verification checkpoint

All R1/R2/R3/R4/R5/R6/R8/R9/R10/R13 core changes are present on main. The latest CI run is intentionally re-evaluated after the consolidated style/test fixes.
