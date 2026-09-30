# Providers

The MVP ships with a deterministic local provider and an OpenAI-compatible adapter.

## Local

`ATTRACTOR_PROVIDER=mock`

No network or credentials are required. Its output is deliberately marked as non-independent.

## OpenAI-compatible

Set:

`ATTRACTOR_PROVIDER=openai-compatible`

`OPENAI_API_KEY=...`

Optional:

`OPENAI_BASE_URL=https://api.openai.com/v1`

`ATTRACTOR_MODEL=...`

The adapter uses a standard OpenAI-compatible `/chat/completions` contract. It is an execution provider, not an evidence source by itself.

## Search

`HttpSearchProvider` defines a vendor-neutral JSON search boundary. A production search adapter must document its endpoint contract, authentication, licensing, rate limits and evidence provenance.
