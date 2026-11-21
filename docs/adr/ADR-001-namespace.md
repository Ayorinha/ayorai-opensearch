# ADR-001 — Isolated Python Namespace

**Status:** Accepted — 2026-11-21, decisão do mantenedor (DEC-003, opção 1). Proposed in A1 PR em 2026-09-30.  
**Date:** 2026-09-30

## Decision

Adopt a `src/` layout with `ayorai_attractor` as the sole application namespace.

The package structure is:

- `ayorai_attractor.agents`
- `ayorai_attractor.api`
- `ayorai_attractor.brain`
- `ayorai_attractor.cli`
- `ayorai_attractor.evidence`
- `ayorai_attractor.evaluation`
- `ayorai_attractor.failure_engine`
- `ayorai_attractor.memory`
- `ayorai_attractor.mcp_gateway`
- `ayorai_attractor.observability`
- `ayorai_attractor.plugins`
- `ayorai_attractor.providers`
- `ayorai_attractor.security`
- `ayorai_attractor.orchestrator`
- `ayorai_attractor.router`
- `ayorai_attractor.research_contract`
- `ayorai_attractor.models`

The current implementation keeps `orchestrator.py`, `router.py`, `research_contract.py`, and `models.py` as modules at the package root, matching the requested logical namespace without introducing unnecessary wrapper packages.

## Rationale

Top-level `mcp` and `agents` collide with the official Model Context Protocol Python SDK and OpenAI Agents SDK namespaces. Other generic top-level names also create avoidable import ambiguity.

The isolated namespace prevents local project modules from shadowing installed SDKs and makes editable/package installs behave consistently.

## Compatibility proof

The A1 CI must install the official `mcp` and `openai-agents` packages and verify that:

1. `import mcp` resolves to the installed SDK.
2. `import agents` resolves to the OpenAI Agents SDK.
3. `import ayorai_attractor` resolves to the project package.
4. The complete test suite passes.

Official SDK installation follows the documented package names: `mcp` and `openai-agents`.

## Consequences

- All application imports use `ayorai_attractor.*`.
- The repository uses `src/` packaging.
- The old top-level generic package directories are removed.
- Future MCP and Agents SDK adoption can use their official namespaces without local shadowing.

## Nota de aceitação (2026-11-21)

Conferência feita na aceitação, sem alterar a decisão:

- Todo o código de aplicação está em `src/ayorai_attractor`, e nenhum pacote genérico de nível superior permanece.
- Os pacotes listados acima existem. Depois de 2026-09-30 entraram `ayorai_attractor.verification` (pipeline de verificação e Judges) e `ayorai_attractor.auditlog` (biblioteca da ADR-010), dentro do mesmo namespace, como a decisão prevê.
- A prova de compatibilidade roda no CI, no job `namespace-compatibility`: `import mcp` e `import agents` resolvem para os SDKs instalados em `site-packages`.
