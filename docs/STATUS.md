# AYORAI ATTRACTOR — Status

**Updated:** 2026-09-30  
**Baseline:** `baf0a82372b0e3053bc7bd66968fb8db495f2b5e`  
**Current phase:** Phase 0 / A2.2

| Capability | Status |
|---|---|
| FastAPI API | VERIFIED |
| CLI | VERIFIED |
| Planner / Researcher / Critic / Fact Checker / Chief Judge | VERIFIED |
| 26 agent roles | DECLARED — 26 roles defined; subset executable |
| Adaptive routing | VERIFIED |
| Evidence store | VERIFIED |
| Evidence graph | VERIFIED |
| Failure Engine | VERIFIED |
| MCP Gateway MVP | VERIFIED |
| Plugin Registry | VERIFIED |
| OpenSearch provider | VERIFIED |
| OpenAI-compatible provider | VERIFIED |
| Mock provider | VERIFIED |
| Docker execution | VERIFIED |
| Ruff | VERIFIED on baseline; A1 final CI pending |
| mypy non-strict | VERIFIED on baseline |
| pytest | VERIFIED on baseline |
| Bandit | VERIFIED on baseline |
| pip-audit | VERIFIED on baseline |
| CodeQL | VERIFIED on baseline |
| Dependabot | VERIFIED |
| Isolated `src/ayorai_attractor` namespace | VERIFIED — A1 merged |
| Official MCP SDK coexistence | VERIFIED — A1 CI proof |
| Official OpenAI Agents SDK coexistence | VERIFIED — A1 CI proof |
| Coverage ratchet | VERIFIED — true monotonic ratchet; baseline 69%; increases and decreases fail until baseline is reconciled |
| Strict mypy job | MISSING — A3 |
| Golden Set v0 | MISSING — A4 |
| Baseline evaluation metrics | NOT MEASURED |
| Hybrid BM25 + kNN + RRF | MISSING |
| Cross-encoder reranking | MISSING |
| Claim decomposition at target level | MISSING |
| SUPPORTS/CONTRADICTS classifier | MISSING |
| Source-independence clustering | MISSING |
| Contradiction detector | MISSING |
| Deterministic Chief Judge at target specification | MISSING — R1 |
| Run Bundle / replay | MISSING |
| Hash-chained audit | MISSING |
| OpenTelemetry / GenAI tracing | MISSING |
| Cost tracking | MISSING |
| Golden smoke/regression gates | MISSING |
| Red-team CI / OWASP ASI mapping | MISSING |
| GEPA / Evolution Engine | MISSING |
| Attractor Studio | MISSING |
| Multi-tenant / durable execution / queue / SSE | MISSING |

A capability is changed from the Phase 0 baseline only when repository evidence or CI verifies it. No evaluation metric is invented.


## A2.2 — Coverage map (verified by CI)

Measurement source: CI run 36748347025, Python 3.13.15.  
Result: **535 statements, 165 missed, 69% total coverage**; 18 tests passed.  
The same ratchet passed at 69% against the 69% baseline.

| Module | Stmts | Miss | Cover |
|---|---:|---:|---:|
| `ayorai_attractor/__init__.py` | 1 | 0 | 100% |
| `agents/core.py` | 50 | 10 | **80%** |
| `agents/roles.py` | 7 | 0 | 100% |
| `api/app.py` | 11 | 0 | 100% |
| `cli/main.py` | 10 | 10 | 0% |
| `evaluation/bench.py` | 8 | 0 | 100% |
| `evidence/core.py` | 23 | 4 | **83%** |
| `evidence/graph.py` | 28 | 0 | 100% |
| `failure_engine/core.py` | 10 | 4 | 60% |
| `mcp_gateway/gateway.py` | 32 | 3 | 91% |
| `memory/core.py` | 17 | 17 | 0% |
| `models.py` | 59 | 0 | 100% |
| `observability/audit.py` | 13 | 13 | 0% |
| `orchestrator.py` | 32 | 5 | 84% |
| `plugins/registry.py` | 26 | 4 | 85% |
| `providers/base.py` | 14 | 1 | 93% |
| `providers/catalog.py` | 18 | 18 | 0% |
| `providers/factory.py` | 21 | 2 | 90% |
| `providers/http_search.py` | 25 | 12 | 52% |
| `providers/mock.py` | 6 | 0 | 100% |
| `providers/openai_compatible.py` | 30 | 13 | 57% |
| `providers/opensearch.py` | 39 | 23 | 41% |
| `providers/registry.py` | 12 | 3 | 75% |
| `research_contract.py` | 9 | 9 | 0% |
| `router.py` | 20 | 0 | 100% |
| `security/policy.py` | 14 | 14 | 0% |

Zero-statement `__init__.py` modules report 100% and are omitted from the detailed table.

### R1 gate check

- **EvidenceStore / `evidence/core.py`: 83% — above the 80% gate.**
- **Judge:** there is no dedicated Judge module yet; the current `JudgeAgent` is in `agents/core.py`, which is **80%** covered.
- No coverage-driven test addition is required by the A2.2 80% gate for evidence or the current Judge location.
- Other low-coverage modules remain tracked as technical debt; A2.2 does not silently reclassify them as R1-ready.

### A2.1 verification

PR #9 was merged after CI passed on Python 3.11, 3.12 and 3.13 plus namespace compatibility. The ratchet now:
1. fails when measured coverage is below baseline;
2. fails when the floored measured coverage is above baseline, with the exact value to record;
3. passes when the floored measured coverage equals the baseline.

No baseline increase was needed because the verified measurement remained 69%.
