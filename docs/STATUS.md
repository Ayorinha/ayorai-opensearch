# AYORAI ATTRACTOR — Status

**Updated:** 2026-09-30  
**Baseline:** `baf0a82372b0e3053bc7bd66968fb8db495f2b5e`  
**Current phase:** Phase 0 / A1

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
| Coverage ratchet | VERIFIED — baseline 69%; CI fails below baseline |
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
