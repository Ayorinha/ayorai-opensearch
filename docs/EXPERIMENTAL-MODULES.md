# Experimental modules

Updated: 2026-10-18

For the current, code-checked boundary between the service entrypoints and the library, see [Manual Técnico — capítulo 02: Arquitetura](manual/02-arquitetura.md). This list is a subset of explicitly documented experimental modules, not a complete inventory of every module outside the API/CLI import paths. The 26 entries in `agents/roles.py` are role metadata; `orchestrator.py` currently wires five concrete agent classes.

The modules below ship in the `ayorai_attractor` package but are **not used** by the verification pipeline, the deterministic Judge, the evaluation runners or the public API. They are kept importable so that existing imports of the published package (v0.5.0) do not break. Their interfaces may change without a deprecation period. Behaviour is pinned by `tests/test_experimental_modules.py`.

| Module | Purpose | Notes |
|---|---|---|
| `ayorai_attractor.memory.core` | In-memory key/value store for research notes | No persistence. |
| `ayorai_attractor.observability.audit` | In-memory audit event log | Distinct from the persistent API audit store. |
| `ayorai_attractor.observability.opentelemetry` | `TraceSink` adapter that exports trace events as OpenTelemetry spans | Requires the optional `telemetry` extra; raises `RuntimeError` without it. Cannot change verification results. |
| `ayorai_attractor.providers.catalog` | Registry of provider metadata, filtered by capability | Disabled providers are excluded. |
| `ayorai_attractor.research_contract` | Declarative research requirements (Pydantic) | Validation only. |
| `ayorai_attractor.security.policy` | Capability allow-list for tool calls | Deny by default. **`requires_approval` is recorded but not enforced by `authorize()`**; any future caller must check it. |

Promoting a module out of this list requires a pull request that wires it into a production path with its own tests and documentation.
