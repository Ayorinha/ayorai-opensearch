# ATTRACTOR Red-Team Contract

R7 establishes a deterministic, executable security corpus for the verification
boundary. Attack-shaped text is treated as untrusted data; it is never promoted
to system instructions.

## Covered classes

- prompt injection;
- evidence poisoning;
- citation manipulation;
- secret leakage.

Each case has an explicit safe-handling action and a stable identifier. The
corpus is intentionally small at this stage so failures remain reviewable and
reproducible.

## Security boundary

The red-team corpus is a regression contract, not a claim that the system is
secure against all attacks. Production deployments still require authorization,
least privilege, secret management, isolation, rate limits, dependency
management and continuous adversarial testing.

A future expansion should add tool abuse, indirect prompt injection, retrieval
poisoning, multi-tenant isolation and protocol-level attacks, with each case
mapped to an identified threat taxonomy and an executable expected outcome.
