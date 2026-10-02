# AYORAI ATTRACTOR

[![CI](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/ci.yml) [![Security](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/security.yml) [![CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml/badge.svg)](https://github.com/Ayorinha/ayorai-opensearch/actions/workflows/codeql.yml)

**AYORAI ATTRACTOR — Evidence-first claim-level verification engine**

> Many Models. One Intelligence Layer. Verified Results.

## Current status

**Reference implementation in active development.** Phase 0 is complete and the deterministic R1 verification core is implemented; R2/R3/R4/R5/R6/R8/R9/R10/R13 engineering cores are also present and tested. The repository deliberately distinguishes verified capabilities from roadmap work.

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

The deterministic audit core is exposed through `POST /v1/audit`. It executes the same request contract as `/v1/opensearch` and returns a typed audit report containing the trace ID, verification state, evidence counts, failure count and deterministic findings. Audit output describes the response; it does not alter the verdict.

## Architecture

- adaptive orchestration and quality modes
- Planner, Researcher, Critic, Fact Checker and Judge extension point
- Evidence Store and Evidence Graph
- Failure Engine
- MCP Gateway and plugin registry
- OpenSearch-compatible and OpenAI-compatible adapters
- deterministic mock provider
- FastAPI API and CLI
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

This is intentionally a **reference architecture and research/engineering platform**, not a claim of universal factual accuracy.

## Verified engineering evidence

- Python 3.11–3.13 CI
- frozen golden v0: 34 cases / 52 documents / SHA-256 manifest
- baseline accuracy: **43.3333%**, equal to the majority-class baseline
- R1 deterministic verification core with unit and property tests

## Roadmap

**Phase 0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12 → R13**

R1 deterministic core is implemented and exposed through POST /v1/verify, with an independent six-verdict Judge regression suite and a post-v0 Golden v1 provenance edge case. Frozen Golden v0 remains the end-to-end engine fixture suite. R2 adds audit/replay operation; R3 adds controlled multi-model deliberation; R5 introduces real hybrid retrieval.

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

See [`docs/eval/LOCAL-EVALUATION.md`](docs/eval/LOCAL-EVALUATION.md), [`docs/STATUS.md`](docs/STATUS.md), [`docs/architecture.md`](docs/architecture.md), [`docs/eval/TRACEABILITY.md`](docs/eval/TRACEABILITY.md) and [`evals/golden/REVIEW.md`](evals/golden/REVIEW.md).

## Security

Never place secrets, personal data, financial records or confidential institutional material in examples or tests. Production integrations must enforce authorization, audit logging, rate limits and data minimization.

## License

Apache-2.0. See LICENSE.