# Deterministic Judge Evaluation

The Judge is evaluated independently from retrieval and generation.

## Contract

Each fixture supplies four explicit inputs:

1. a structured claim;
2. structured evidence with provenance;
3. explicit stance edges;
4. the expected Judge verdict.

The fixture never supplies an expected verdict to the Judge. The Judge receives only the claim, evidence, and stance graph.

This separation prevents the evaluation harness from silently using an LLM or the gold label as a decision-maker.

## v0 coverage

The judge fixture suite contains one deterministic fixture for each ADR-002 verdict:

- VERIFIED
- SUPPORTED
- PARTIALLY_SUPPORTED
- CONFLICTING
- REFUTED
- UNVERIFIED

The CI gate requires all six fixtures to pass.

## Scope

This suite validates the deterministic decision layer. It does not measure retrieval recall, claim extraction quality, or source ranking. Those metrics remain separate so a Judge regression cannot be hidden by upstream model behavior.\n## Public smoke fixture\n\nThe single-case public Judge smoke fixture is `evals/golden/judge-smoke.jsonl`. The name **Golden v1** is reserved for the future hidden Portuguese Golden v1 set and is intentionally not used by this public fixture.\n\n