# AYORAI ATTRACTOR

**AYORAI ATTRACTOR — Evidence-first claim-level verification engine**

> Many Models. One Intelligence Layer. Verified Results.

## Current status

**Phase 0 — completed. R1 core implemented on main.** The deterministic verification core now includes evidence clustering, numeric/date rules, a six-state Judge, provenance completeness, abstain contracts and response-secret scanning.

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

## Verified engineering evidence

- Python 3.11–3.13 CI
- frozen golden v0: 34 cases / 52 documents / SHA-256 manifest
- baseline accuracy: **43.3333%**, equal to the majority-class baseline
- R1 deterministic verification core with unit and property tests

## Roadmap

**Phase 0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12 → R13**

R1 core is implemented. The next integration milestone is executing the deterministic Judge against Golden v0. R2 adds audit/replay operation; R3 adds controlled multi-model deliberation; R5 introduces real hybrid retrieval.

## Quickstart

    python -m venv .venv
    pip install -e ".[dev]"
    uvicorn ayorai_attractor.api.app:app --reload

CLI:

    opensearch "compare RAG and fine-tuning"

API:

    POST /v1/opensearch

## Security

Never place secrets, personal data, financial records or confidential institutional material in examples or tests. Production integrations must enforce authorization, audit logging, rate limits and data minimization.

## License

Apache-2.0. See LICENSE.