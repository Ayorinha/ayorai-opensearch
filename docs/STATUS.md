# AYORAI ATTRACTOR — Engineering Status

**Updated:** 2026-10-03  
**Default branch:** `main`  
**Current implementation:** Phase 0 + deterministic R1 + R2/R3/R4/R5/R6/R8/R9/R10/R13 cores  
**Evaluation ground truth:** 34 cases / 52 synthetic documents

This document is intentionally evidence-based: a capability is marked **VERIFIED** only when code, tests, repository artifacts, or CI provide direct evidence. Roadmap items are not presented as implemented.

## Reference-grade capability map

| Area | Status | Evidence |
|---|---|---|
| Deterministic claim verification | VERIFIED | `verification/judge.py`, numeric/date rules, tests |\n| Claim-level pipeline contracts | IMPLEMENTED / NOT YET GOLDEN-VERIFIED | `verification/extraction.py`, `verification/stance.py`, `verification/claim_pipeline.py` + tests |
| Evidence provenance | VERIFIED | structured evidence model + provenance checks |
| Source-independence clustering | VERIFIED | `verification/clusters.py` + tests |
| Contradiction handling | VERIFIED | deterministic stance/judge model |
| Abstention contracts | VERIFIED | response/security tests |
| Audit mode | VERIFIED | `audit.py` + tests |
| Replay / content addressing | VERIFIED | `replay.py` + tests |
| Council / controlled deliberation core | VERIFIED | `council.py` + tests |
| Hybrid rank fusion | VERIFIED | `hybrid.py` + tests |
| Durable checkpoint core | VERIFIED | `durable.py` + tests |
| Cost / latency metrics primitives | VERIFIED | `metrics.py` + tests |
| Governance checks | VERIFIED | `governance.py` + tests |
| MCP gateway | VERIFIED | gateway implementation + tests |
| Provider adapters | VERIFIED | OpenSearch, OpenAI-compatible and mock providers |
| FastAPI API | VERIFIED | `api/app.py` + tests |
| CLI | VERIFIED | `cli/main.py` + tests |
| Docker execution | VERIFIED | Dockerfile + compose |
| Golden v0 closed-world fixture | VERIFIED | 34 cases / 52 documents / SHA-256 manifest |
| Golden smoke CI | VERIFIED | blocking CI job |
| Full Golden v0 regression | BLOCKING CI | 34-case job; report uploaded as artifact |
| Python compatibility | VERIFIED | CI matrix 3.11 / 3.12 / 3.13 |
| Ruff | VERIFIED | blocking CI |
| mypy | BLOCKING | blocking non-strict type check |
| strict evidence typing | VERIFIED | blocking strict evidence check |
| Security audit | VERIFIED | pip-audit + Bandit |
| CodeQL | VERIFIED | CodeQL v4 workflow |
| Dependabot | VERIFIED | repository configuration |
| Community health | VERIFIED | README, LICENSE, SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, issue forms |

## Evaluation truth

The frozen Golden v0 is a **deterministic motor-verification fixture suite**. It is not a real-web retrieval benchmark and must not be interpreted as proof of general-world factuality.

The recorded majority-class baseline is **43.3333%**. Any future benchmark claim must report the dataset version, case count, corpus count, suite, system commit and reproducibility artifacts.

## Remaining engineering frontier

These are intentionally still separate from the verified core:

- production-grade hybrid retrieval against a real index;
- cross-encoder / learned reranking;
- Golden v0 integration through the new claim-level pipeline;\n- target-level claim decomposition and automated stance extraction;
- production OpenTelemetry / GenAI semantic conventions;
- durable external queue / worker execution;
- multi-tenant authorization and isolation;
- streaming/SSE production API;
- adversarial red-team suite mapped to current agent-security guidance;
- larger independently curated evaluation sets;
- published reproducible comparisons against external baselines.

The project should advance these only with executable implementations, tests, measured results and documentation. No roadmap item should be promoted to VERIFIED merely because an interface exists.

## Quality gates

A merge-ready change should preserve:

1. deterministic tests;
2. Python 3.11–3.13 compatibility;
3. Ruff and mypy;
4. coverage non-regression;
5. Golden contract integrity;
6. security scans;
7. reproducible evaluation artifacts.

## Maintainer principle

**Evidence before claims. Determinism before persuasion. Reproducibility before benchmarks.**

That principle is the standard for ATTRACTOR itself.


## P0 claim-level verification boundary

The new P0 path separates learned/advisory components from the deterministic Judge:

`retrieval → ClaimExtractor → StanceDetector → ADR-002 Judge → ResponseStatus`.

Three adapter families are defined for claim extraction and stance detection:

1. deterministic rule/fixture implementations for CI;
2. injected local NLI implementations (for example MiniCheck/DeBERTa-class backends);
3. provider-backed LLM implementations.

Each learned output carries component/model/version and input/output SHA-256 provenance. These components may produce Claims and StanceEdges only; they never select a final Verdict.

**Important:** this increment establishes the contracts and executable unit tests. It does **not** claim that Golden v0 is now improved. The Golden runner still requires a separate integration increment before any benchmark number changes.
