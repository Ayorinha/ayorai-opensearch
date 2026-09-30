# AYORAI ATTRACTOR

Adaptive Multi-Agent Intelligence & Verification Engine.

> Many Models. One Intelligence Layer. Verified Results.

AYORAI ATTRACTOR is an evidence-first AI orchestration foundation. It separates cognitive roles from execution providers and routes work according to capability, quality, latency, cost and risk.

## Package layout

The application uses a `src/` layout and a single project namespace:

```
src/ayorai_attractor/
├── agents/
├── api/
├── brain/
├── cli/
├── evidence/
├── evaluation/
├── failure_engine/
├── memory/
├── mcp_gateway/
├── observability/
├── plugins/
├── providers/
├── security/
├── models.py
├── orchestrator.py
├── research_contract.py
└── router.py
```

This prevents the project from shadowing the official `mcp` and `agents` SDK namespaces.

## MVP

- FastAPI: POST /v1/opensearch
- CLI: opensearch
- Planner, Researcher, Critic, Fact Checker and Judge
- evidence records, Evidence Graph and verification states
- failure-aware execution
- fast, balanced and deep quality modes
- deterministic local provider
- optional HTTPS external-search adapter
- OpenSearch-compatible read-only adapter
- tests, CI, security scanning and Dependabot

The MVP does not pretend that a local mock is internet verification. External search is an explicit adapter; its results are tracked separately from model output.

## Quickstart

    python -m venv .venv
    pip install -e ".[dev]"
    uvicorn ayorai_attractor.api.app:app --reload

Then:

    opensearch "compare RAG and fine-tuning"

API:

    POST /v1/opensearch

## Official SDK namespace regression

Development dependencies include the official Python packages `mcp` and `openai-agents`. CI verifies that:

- `import mcp` resolves to the installed MCP SDK;
- `import agents` resolves to the OpenAI Agents SDK;
- `import ayorai_attractor` resolves to this project.

## Security

Never place secrets, personal data, financial records or confidential institutional material in examples or tests. Production integrations must enforce authorization, audit logging, rate limits and data minimization.

## License

Apache-2.0. See LICENSE.
