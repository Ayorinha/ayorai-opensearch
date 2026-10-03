# AYORAI ATTRACTOR — Progress

**Estado atual:** Fase 0 concluída; R1 core implementado; R2–R13 possuem fundamentos de engenharia testados no main. R14 adiciona contexto de tracing provider-neutral integrado ao orquestrador. R15 adiciona a fronteira de execução durável sobre o JobStore. R16 adiciona revisão automatizada de dependências em pull requests. R17 adiciona uma fronteira provider-neutral para exportação de eventos de tracing. R18 propaga um TenantContext confiável da fronteira de runtime para o AgentContext, sem transformar dados do pedido em autorização.

**Main de referência atual:** 1d8e1ee24933d4a7e6d9b22bf247d88de469f367 (merge de R17).

**Ground Truth:** 34 casos / 52 documentos sintéticos.
**Baseline:** 43,3333%, exatamente igual à classe majoritária PARTIALLY_SUPPORTED. Esse número não demonstra capacidade de verificação.

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
| R14 | implementação integrada | TraceContext + eventos no orchestrator |
| R15 | implementação integrada | JobExecutor + lifecycle do JobStore + testes |
| R16 | implementação integrada | Dependency Review workflow |
| R17 | implementação integrada | TraceSink export boundary + testes |
| R18 | implementação integrada | TenantContext propagado ao AgentContext + teste |

## Princípio de conclusão

Uma etapa só é considerada concluída quando existe implementação executável, teste automatizado e evidência de integração apropriada. Documentação aspiracional não conta como implementação.

## Próximos gargalos

1. executar e publicar o harness Golden completo com relatórios estatísticos reproduzíveis;
2. adapter OpenTelemetry atrás da fronteira TraceSink, sem acoplamento semântico ao Judge;
3. transport-level MCP e isolamento de ferramentas;
4. adapter de modelos/providers modernos sem delegar o Judge;
5. hardening de deployment, SBOM e release reproduzível;
6. verificação explícita de CI/security/CodeQL para os commits mais recentes;
7. auditoria final de documentação, testes e claims de segurança.

## Segurança e qualidade

O repositório mantém CI, cobertura, typing, Bandit, pip-audit e CodeQL no ciclo de desenvolvimento. Dependency Review/Dependabot e secret scanning devem ser tratados como controles de plataforma GitHub quando disponíveis para a conta e para o repositório.

O objetivo de referência é demonstrar **código → teste → CI → segurança → benchmark → reprodutibilidade → arquitetura → auditoria → documentação**, sem declarar superioridade universal sobre todos os projetos do GitHub.
