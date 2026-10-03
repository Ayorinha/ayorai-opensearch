# AYORAI ATTRACTOR — Progress

**Estado atual:** Fase 0 concluída; R1 core implementado; R2–R13 possuem
fundamentos de engenharia testados no main. R14 adiciona contexto de tracing
provider-neutral integrado ao orquestrador. As integrações de produção,
execução distribuída e hardening operacional continuam sendo tratadas
separadamente.

**Main de referência antes de R14:** `2226e7c6820aa453703eaa42cf3beeca7e7df55b`.

**Ground Truth:** 34 casos / 52 documentos sintéticos.
**Baseline:** 43,3333%, exatamente igual à classe majoritária
PARTIALLY_SUPPORTED. Esse número não demonstra capacidade de verificação.

## Estado por etapa

| Etapa | Estado | Evidência |
|---|---|---|
| Fase 0 | concluída | Golden v0 congelado + manifesto SHA-256 |
| R1 | core implementado | Judge determinístico + testes |
| R2 | fundação implementada | Audit API + SQLite/replay metadata |
| R3 | fundação implementada | Council + isolamento de falhas |
| R4 | fundação implementada | ReplayStore content-addressed |
| R5 | fundação implementada | Hybrid OpenSearch + RRF |
| R6 | fundação implementada | grounded synthesis gate + pipeline R1→R6 |
| R7 | fundação implementada | red-team corpus determinístico |
| R8 | fundação implementada | métricas + Prometheus text export |
| R9 | fundação implementada | JobStore + idempotência + leases |
| R10 | fundação implementada | arena + bootstrap + McNemar |
| R11 | fundação implementada | bounded optimizer |
| R12 | fundação implementada | MCP/plugin governance boundary |
| R13 | fundação implementada | TenantContext imutável |
| R14 | em implementação | TraceContext integrado ao orchestrator |

## Princípio de conclusão

Uma etapa só é considerada concluída quando existe implementação executável,
teste automatizado e evidência de integração apropriada. Documentação
aspiracional não conta como implementação.

## Próximos gargalos

1. exportação OpenTelemetry sem acoplamento semântico ao Judge;
2. propagação de tenant context nas superfícies de runtime e autorização;
3. integração real do JobStore ao executor/worker;
4. harness Golden automatizado com relatórios estatísticos reproduzíveis;
5. transport-level MCP e isolamento de ferramentas;
6. adapter para provedores modernos de modelos sem delegar o Judge;
7. hardening de deployment, supply chain e release reproducível.

## Segurança e qualidade

O repositório mantém CI, cobertura, typing, Bandit, pip-audit e CodeQL no ciclo
de desenvolvimento. Dependency Review/Dependabot e secret scanning devem ser
tratados como controles de plataforma GitHub quando disponíveis para a conta e
para o repositório.

O objetivo de referência é demonstrar **código → teste → CI → segurança →
benchmark → reprodutibilidade → arquitetura → auditoria → documentação**,
sem declarar superioridade universal sobre todos os projetos do GitHub.
