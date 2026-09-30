# AYORAI ATTRACTOR

Adaptive Multi-Agent Intelligence & Verification Engine.

> Many Models. One Intelligence Layer. Verified Results.

AYORAI ATTRACTOR is an evidence-first AI orchestration foundation. It separates cognitive roles (agents) from execution engines (models/providers) and routes work according to capability, quality, latency, cost and risk.

## MVP

- FastAPI: POST /v1/opensearch
- CLI: opensearch
- Planner, Researcher, Critic, Fact Checker and Judge
- evidence records, Evidence Graph and verification states
- failure-aware execution
- fast, balanced and deep quality modes
- deterministic local provider, so the project runs without API keys
- optional HTTPS external-search adapter via `ATTRACTOR_SEARCH_ENDPOINT`
- tests, CI, security scanning and Dependabot

The MVP intentionally does not pretend that a local mock is internet verification. External search is an explicit, HTTPS-only adapter; its results are tracked separately from model output and feed the Evidence Graph. A single independent source is classified as partial support; multiple independent sources can reach supported status, while verified status still requires explicit verification flags.

## Architecture

User -> API/CLI -> ATTRACTOR Brain -> Adaptive Agent Swarm -> Evidence -> Failure Engine -> Judge -> Result

Core principle: Agent != Model. A role is a cognitive function; a provider is an execution engine.

## Quickstart

    python -m venv .venv
    pip install -e ".[dev]"
    uvicorn attractor.api.app:app --reload

Then:

    opensearch "compare RAG and fine-tuning"

API:

    POST /v1/opensearch

Example JSON body:

    {"query":"compare RAG and fine-tuning","mode":"balanced"}

## Evolution roadmap

1. Real search and LLM adapters.
2. Adaptive N-agent allocation; 26 initial roles, no hard maximum.
3. RAG, graph memory and MCP tool gateway.
4. Multimodal providers.
5. AI Scout and Technology Radar.
6. Sandboxed AI Lab and Evolution Engine.
7. ATTRACTOR-Bench and multidimensional evaluation.
8. Distributed execution, observability, canary and rollback.

Continuous improvement follows: DISCOVER -> VERIFY -> SECURITY CHECK -> EXPERIMENT -> BENCHMARK -> CANARY -> PROMOTE / ROLLBACK.

No uncontrolled production self-modification.

## Security

Never place secrets, personal data, financial records or confidential institutional material in examples or tests. Production integrations must enforce authorization, audit logging, rate limits and data minimization.

## License

Apache-2.0. See LICENSE.
