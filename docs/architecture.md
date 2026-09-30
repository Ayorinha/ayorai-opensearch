# Architecture

## Core layers

### Brain
Owns orchestration policy, routing and execution budgets.

### Agents
An agent is a cognitive role, not a model. Multiple agents can share one provider, and one agent can be evaluated across multiple providers.

### Providers
Providers expose capabilities such as reasoning, search, embeddings or local inference. Registry metadata will evolve to include health, latency, cost and benchmark scores.

### Evidence
Externally grounded claims should carry provenance. The target graph is:

question -> claim -> source -> extract -> cross-check -> contradiction -> verification

### Failure Engine
Failures are first-class data. Recoverable failures should trigger retry, fallback or replanning; blocking failures should stop unsafe execution.

### Evolution
Future self-improvement is sandboxed:

DISCOVER -> VERIFY -> SECURITY CHECK -> EXPERIMENT -> BENCHMARK -> CANARY -> PROMOTE / ROLLBACK

No production component should rewrite itself without an explicit promotion boundary.
