# ADR-006 — Deterministic Metadata, Independence and Numeric Semantics

Status: Accepted for F1.1  
Date: 2026-10-03

## Decision

F1.1 formalizes metadata semantics before any Golden v0 measurement. These rules are normative and are not tuned against Golden v0.

### 1. Evidence independence

Two evidence items are dependent when any deterministic relation below is established:

1. same canonical URL;
2. same origin identifier;
3. same source identifier;
4. same normalized-content hash;
5. direct citation/republication relation where one item's cited origin equals the other's origin.

Dependency is transitive. A publication chain therefore forms one dependency cluster even when the final URLs differ.

Missing dependency metadata is UNKNOWN, not evidence of independence. Different domains, URLs or source labels alone do not prove independence.

The Judge counts supporting and contradicting clusters, not raw evidence items. This prevents republications and copied text from being counted as independent corroboration.

### 2. Provenance completeness

Supporting evidence is provenance-complete only when:

- provenance_complete is true;
- source offsets are valid and non-empty;
- the excerpt is non-empty;
- an origin identifier or canonical URL identifies the source.

Incomplete provenance never upgrades a claim to VERIFIED. It can support a lower-confidence verdict when the required number of independent supporting clusters exists.

### 3. Numeric semantics

Numeric comparison is deterministic and uses the locale declared for the source.

The relative difference is abs(x-y) / max(abs(x), abs(y)). When both values are below the zero threshold, the relative difference is zero.

A pair is contradictory only when the semantic attribute matches, the unit matches, parsing succeeds under the selected locale, and relative difference is strictly greater than the frozen tolerance.

Therefore the tolerance boundary is inclusive: equality at the tolerance is agreement.

Numeric agreement is a hard SUPPORTS signal and must be evaluated before lexical/NLI inference. Numeric contradiction is a hard CONTRADICTS signal and cannot be overridden by NLI.

Ambiguous locale formatting must fail closed rather than be silently reinterpreted.

### 4. Dates, units and negation

Date contradictions compare at the granularity asserted by the claim. Unit-bearing quantities must have compatible units before numerical comparison. Explicit PT/EN negation is a deterministic contradiction signal.

### 5. Judge boundary

These rules emit evidence-level stance semantics only. ADR-002 remains the sole authority for the final verdict and global precedence.

## Independent tests

F1.1 unit tests cover same-source dependency, same-hash dependency, citation/republication transitivity, unknown dependency metadata, numeric agreement inside tolerance, inclusive tolerance boundary, and contradiction beyond tolerance even with low lexical overlap.

The tests do not import or inspect Golden v0 cases.

## Measurement protocol

Only after these tests pass may the Golden v0 evaluation be run. Golden v0, its SHA-256, and frozen thresholds remain unchanged.
