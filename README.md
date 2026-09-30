# AYORAI ATTRACTOR

**AYORAI ATTRACTOR — Evidence-first claim-level verification engine**

> Many Models. One Intelligence Layer. Verified Results.

## Current status

**Phase 0 — completed.** Golden v0 is frozen at **34 cases / 52 synthetic documents** with SHA-256 recorded in `evals/golden/MANIFEST.json`. The current-system baseline is **43.3333%**, exactly equal to the `PARTIALLY_SUPPORTED` majority-class baseline. **R1 is the next implementation phase; its motor is not yet implemented.**

Baseline evidence: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/36759101933  
Baseline report: `docs/eval/BASELINE-v0.md`  
Phase 0 progress: `docs/PROGRESS.md`

## What problem does it solve?

LLM-generated citations can exist without actually supporting the claim they are attached to. ATTRACTOR is designed to make verification explicit: evidence is modeled separately from model output, source independence and provenance are first-class concepts, conflicts are represented, and a deterministic verification contract is defined before the target verification engine is implemented.

The frozen v0 is a **motor-verification fixture suite**, not a retrieval benchmark. It does not claim real-web search quality or generalization.

## Architecture

- adaptive orchestration and quality modes
- Planner, Researcher, Critic, Fact Checker and current Judge extension point
- Evidence Store and Evidence Graph
- Failure Engine
- MCP Gateway and plugin registry
- OpenSearch-compatible and OpenAI-compatible adapters
- deterministic mock provider
- FastAPI API and CLI
- CI, coverage ratchet, strict typing and security scanning

## Verified engineering evidence

- Python 3.11–3.13 CI
- 73% coverage ratchet verified by GitHub Actions
- strict mypy repository check with blocking strict evidence-core check
- frozen golden v0: 34 cases / 52 documents / SHA-256 manifest
- baseline published as a GitHub Actions artifact
- baseline accuracy: **43.3333%**, equal to the majority-class baseline

## Baseline honesty

The current system predicts `PARTIALLY_SUPPORTED` for every case with evidence. Therefore the 43.3333% accuracy is a baseline behavior, not evidence of a capable verification engine. The 100% injection-resistance figure is trivial in the current offline fixture engine and should not be interpreted as completed injection defense. The reported latency is offline fixture execution, not real search latency.

## Roadmap

**Phase 0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12 → R13**

R1 will implement the approved ADR-002 verification rules, including claim decomposition, evidence clustering, stance/contradiction handling and a deterministic Chief Judge, with v0 and a sealed holdout used for measurement.

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
