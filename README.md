# AYORAI ATTRACTOR

[![CI](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml) [![Security](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml) [![CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml)

**AYORAI ATTRACTOR — Evidence-first claim-level verification engine**

> Many Models. One Intelligence Layer. Verified Results.

## Current status

**Reference implementation in active development.** Phase 0 and the R1 deterministic verification core are implemented. R2–R13 provide tested engineering foundations, R14 adds provider-neutral tracing context, R15 adds durable worker execution over JobStore, R16 adds automated dependency review, R17 adds a provider-neutral trace export boundary, and R18 propagates a trusted TenantContext from the runtime boundary into AgentContext. Production deployment, transport-level MCP, external telemetry adapters and deployment-specific authorization remain explicit hardening work.

Golden v0 remains **34 cases / 52 synthetic documents** with SHA-256 recorded in evals/golden/MANIFEST.json. The original baseline is **43.3333%**, exactly equal to the PARTIALLY_SUPPORTED majority-class baseline. This baseline is not evidence of a capable verifier.

Baseline evidence: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/36759101933
Baseline report: docs/eval/BASELINE-v0.md
Progress: docs/PROGRESS.md

## What problem does it solve?

LLM-generated citations can exist without actually supporting the claim they are attached to. ATTRACTOR makes verification explicit: evidence is modeled separately from model output, source independence and provenance are first-class concepts, conflicts are represented, and the verdict is derived by deterministic rules.

The frozen v0 is a **motor-verification fixture suite**, not a retrieval benchmark. It does not claim real-web search quality or generalization.

## R1 verification core

- deterministic evidence dependency clustering;
- locale-bound numeric parsing and 1% relative tolerance;
- day/month/year date conflict rules;
- deterministic six-state Judge;
- global verdict precedence;
- explicit provenance completeness;
- ABSTAIN/NO_ANSWER and ABSTAIN/OUT_OF_SCOPE contracts;
- recursive evaluation-secret leakage detection.

The Judge does not delegate verdict decisions to an LLM. Instruction-like text inside a retrieved document remains document data; it does not become an instruction to the system.

## R2 Audit API

The deterministic audit core is exposed through POST /v1/audit. It executes the same request contract as /v1/opensearch and returns a typed audit report containing the trace ID, verification state, evidence counts, failure count and deterministic findings. Audit output describes the response; it does not alter the verdict.

## Architecture

- adaptive orchestration and quality modes
- Planner, Researcher, Critic, Fact Checker and Judge extension point
- Evidence Store and Evidence Graph
- Failure Engine
- governed MCP Gateway and plugin registry
- OpenSearch-compatible and OpenAI-compatible adapters
- deterministic mock provider
- FastAPI API and CLI
- durable audit/replay state
- deterministic metrics and comparative evaluation
- tenant-scoping primitives with explicit runtime propagation
- provider-neutral trace events and export boundary
- durable JobExecutor over the leased JobStore
- dependency review and security scanning
- CI, coverage ratchet, strict typing and security scanning

## Why ATTRACTOR is designed for reference use

ATTRACTOR treats verification as an engineering boundary rather than a prompt convention:

- **Deterministic verdicts:** model output cannot directly choose the final verification state.
- **Evidence as data:** provenance, source identity, offsets, independence and stance are explicit structures.
- **Abstention is first-class:** unsupported and out-of-scope requests have explicit contracts.
- **Replayability:** runs can be content-addressed and verified rather than trusted by narrative logs.
- **Closed-world evaluation:** Golden v0 is frozen, hashed and executable in CI.
- **Quality gates:** linting, typing, tests, coverage ratcheting, dependency audit, Bandit and CodeQL are part of the development loop.
- **Provider isolation:** retrieval/model integrations are kept behind provider contracts.
- **Governed tool execution:** MCP/plugin dispatch is allowlisted and trusted-only by default.
- **Explicit tenant boundaries:** trusted control-plane context is propagated explicitly and is never inferred from model output or request text.

This is intentionally a **reference architecture and research/engineering platform**, not a claim of universal factual accuracy.

## Verified engineering evidence

- Python 3.11–3.13 CI
- frozen golden v0: 34 cases / 52 documents / SHA-256 manifest
- baseline accuracy: **43.3333%**, equal to the majority-class baseline
- R1 deterministic verification core with unit and property tests
- R7 adversarial corpus with CI Security/CodeQL coverage
- R8 deterministic metrics primitives with stable Prometheus text export
- R9 durable job state with idempotency, atomic claims and restart-safe leases
- R10 deterministic comparative evaluation arena with bootstrap and paired McNemar statistics
- R11 bounded candidate optimization extension point with explicit evaluation budgets
- R12 governed MCP/plugin boundary
- R13 immutable tenant context primitive
- R14 provider-neutral tracing context integrated with orchestration
- R15 JobExecutor lifecycle over JobStore
- R16 automated Dependency Review workflow
- R17 provider-neutral TraceSink export boundary
- R18 trusted TenantContext propagation into AgentContext with automated coverage

## Roadmap

**Phase 0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12 → R13 → R14 → R15 → R16 → R17 → R18**

The roadmap is implemented in layers rather than declared complete from documentation alone. Remaining hardening increments are the executable Golden statistical harness, an optional OpenTelemetry adapter behind TraceSink, transport-level MCP deployment and isolation, provider adapters, deployment/release hardening, and final CI/security evidence review.

## Quickstart

    python -m venv .venv
    pip install -e ".[dev]"
    uvicorn ayorai_attractor.api.app:app --reload

CLI:

    opensearch "compare RAG and fine-tuning"

API:

    POST /v1/opensearch
    POST /v1/audit
    POST /v1/verify

## Reproducible evaluation

Run the complete frozen suite locally:

    attractor eval --suite golden-v0 --out reports/golden-v0.json

The suite contains 34 cases and 52 synthetic documents. Always report the commit SHA and suite version alongside any result. The CI pipeline executes the complete suite and stores the generated report as a workflow artifact.

See docs/eval/LOCAL-EVALUATION.md, docs/STATUS.md, docs/architecture.md, docs/eval/TRACEABILITY.md and evals/golden/REVIEW.md.

## Security

Never place secrets, personal data, financial records or confidential institutional material in examples or tests. Production integrations must enforce authorization, audit logging, rate limits and data minimization. TenantContext is a propagation primitive; production authorization must be enforced by a trusted control-plane boundary.

## License

Apache-2.0. See LICENSE.
