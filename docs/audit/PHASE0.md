# Phase 0 — Reality Audit Baseline

**Audit date:** 2026-09-30  
**Baseline commit:** `baf0a82372b0e3053bc7bd66968fb8db495f2b5e`  
**Baseline purpose:** immutable "before" snapshot for Phase 0. Future audits must use new files.

## 1. Scope and honesty rule

This document records the Phase 0 diagnosis exactly as established before A1–A4. A capability is **VERIFIED** only when executable evidence, tests, CI output, or repository artifacts prove it. **DECLARED** means documentation/architecture says it exists but the audit did not establish the full target behavior. **PROPOSED/MISSING** means it was identified as roadmap work, not implemented.

## 2. Repository tree observed

```
.
├── agents/
├── attractor/
│   ├── api/
│   ├── brain/
│   ├── cli/
│   ├── models.py
│   ├── orchestrator.py
│   ├── research_contract.py
│   └── router.py
├── evidence/
├── evaluation/
├── failure_engine/
├── memory/
├── mcp/
├── observability/
├── plugins/
├── providers/
├── security/
├── tests/
├── docs/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── security.yml
│   │   └── codeql.yml
│   └── dependabot.yml
├── docker/
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

The project had no `src/` layout at the baseline. `mcp/` and `agents/` were top-level Python packages.

## 3. Counts recorded during the audit

- Relevant Python files: **35**
- Approximate source lines by area:
  - agents: **161**
  - attractor: **286**
  - evidence: **88**
  - evaluation: **29**
  - failure_engine: **23**
  - memory: **38**
  - mcp: **66 code + 17 docs**
  - observability: **33**
  - plugins: **51**
  - providers: **281**
  - security: **23**
  - tests: **172**

These are audit inventory counts, not performance metrics.

## 4. Declared vs existing

| Capability | Status at baseline | Audit finding |
|---|---|---|
| FastAPI API | VERIFIED | `POST /v1/opensearch` exists |
| CLI | VERIFIED | `opensearch` entry point exists |
| Planner / Researcher / Critic / Fact Checker / Chief Judge | VERIFIED | Executable implementations exist |
| 26 agent roles | DECLARED | 26 roles are defined; only a subset is executable |
| Adaptive routing | VERIFIED | Router exists |
| Evidence store | VERIFIED | Basic store exists |
| Evidence graph | VERIFIED | Basic graph exists |
| Failure Engine | VERIFIED | Basic failure handling exists |
| MCP Gateway | VERIFIED | MVP gateway exists |
| Plugin Registry | VERIFIED | Registry with health/cost/latency metadata exists |
| OpenSearch provider | VERIFIED | HTTPS/read-only adapter exists |
| OpenAI-compatible provider | VERIFIED | HTTPS adapter exists |
| Mock provider | VERIFIED | Deterministic local execution exists |
| Docker execution | VERIFIED | Docker configuration exists |
| Ruff | VERIFIED | CI runs Ruff |
| mypy | VERIFIED | CI runs non-strict mypy |
| pytest | VERIFIED | CI runs pytest |
| Bandit | VERIFIED | Security workflow runs Bandit |
| pip-audit | VERIFIED | Security workflow runs pip-audit |
| CodeQL | VERIFIED | CodeQL workflow exists and runs |
| Dependabot | VERIFIED | Configuration exists |
| src layout / namespace isolation | MISSING | Top-level generic packages still exist |
| Official MCP SDK compatibility | MISSING | Namespace collision not yet resolved |
| strict mypy | MISSING | `mypy --strict` not yet established |
| 3.11/3.12/3.13 green matrix | DECLARED at audit time | Existing CI had not yet established the final required Phase 0 gates |
| Coverage ratchet | MISSING | No ratchet gate |
| Golden Set v0 | MISSING | No 20-case corpus/suite |
| Baseline evaluation metrics | NOT MEASURED | No verified measurements |
| Hybrid BM25 + kNN + RRF | MISSING | Not implemented |
| Cross-encoder reranking | MISSING | Not implemented |
| Claim decomposition | MISSING | Not implemented at target level |
| SUPPORTS/CONTRADICTS classifier | MISSING | Not implemented at target level |
| Source-independence clustering | MISSING | Not implemented |
| Contradiction detector | MISSING | Not implemented |
| Deterministic Chief Judge at target specification | MISSING | Existing logic is simpler |
| Run Bundle / replay | MISSING | Not implemented |
| Hash-chained audit | MISSING | Not implemented |
| OpenTelemetry / GenAI tracing | MISSING | Not implemented |
| Cost tracking | MISSING | Not implemented |
| Golden smoke/regression gates | MISSING | Not implemented |
| Red-team CI / OWASP ASI mapping | MISSING | Not implemented |
| GEPA / Evolution Engine | MISSING | Not implemented |
| Attractor Studio | MISSING | Not implemented |
| Multi-tenant / durable execution / queue / SSE progress | MISSING | Not implemented |

## 5. Top 10 risks recorded

1. **Namespace collision:** top-level `mcp` conflicts with the official MCP Python SDK and `agents` conflicts with the OpenAI Agents SDK import namespace.
2. **Generic global package names:** `security`, `memory`, `plugins`, `evaluation`, `evidence`, and `providers` can collide with third-party packages.
3. **Verification semantics too weak:** current evidence status logic does not yet implement the required cluster/provenance/contradiction rules.
4. **No deterministic contradiction engine:** independent contradictory evidence is not yet modeled and adjudicated at the target level.
5. **No Golden Set:** there is no reproducible ground-truth corpus for measuring factuality, citations, abstention, or injection resistance.
6. **No measured baseline:** required evaluation metrics have not been measured; therefore quality claims would be unsupported.
7. **Strict typing not established:** the repository does not yet enforce `mypy --strict` for the target architecture.
8. **No reproducible Run Bundle/replay:** executions cannot yet be fully replayed with immutable evidence/provenance.
9. **Security/evolution controls are incomplete:** red-team gates, benchmark gates, and controlled self-improvement are not implemented at the target level.
10. **Production architecture is incomplete:** durable execution, distributed orchestration, telemetry/cost accounting, and multi-tenant controls remain roadmap work.

## 6. Metrics NOT MEASURED at baseline

The following target metrics were explicitly **NOT MEASURED**:

- Accuracy
- Claim Precision
- Claim Recall
- Citation Accuracy
- Verdict Accuracy
- Expected Calibration Error (ECE)
- Abstention Accuracy
- P95 Latency
- Cost/query
- Attack Blocking Rate

No numeric value is asserted for these metrics in this baseline.

## 7. Phase 0 conclusion

At the audit point, AYORAI ATTRACTOR was a functional **MVP architectural foundation**, not the completed verification platform described by the master specification.

Verified foundations existed for API/CLI orchestration, a subset of agents, evidence storage/graphing, failure handling, MCP gateway MVP, plugin registry, providers, testing and security workflows. The target verification/evaluation architecture remained incomplete.

This file is intentionally frozen as the **before** record. Subsequent findings belong in new audit files.

## 8. Baseline CI evidence

At the end of the requested continuation check, commit `baf0a82` had these completed workflow runs:

- CI run **107** — **SUCCESS**
- Security run **106** — **SUCCESS**
- CodeQL run **105** — **SUCCESS**

These are evidence for the baseline commit only; they do not imply that A1–A4 requirements are complete.

