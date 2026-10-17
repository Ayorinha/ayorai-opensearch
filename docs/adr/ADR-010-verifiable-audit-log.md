# ADR-010: Verifiable audit log

- **Status:** Proposed
- **Date:** 2026-10-17
- **Decision owner:** Anderson Leon Ayora
- **Scope:** Design proposal only; no implementation is authorized by this ADR.

## Context

An auditable verification system needs to explain what was evaluated, which evidence references were considered, which versioned rules produced the result, and whether the retained record has changed since it was created. Ordinary application logs are useful for operations, but they are not by themselves a durable proof of integrity: they can be incomplete, edited, reordered, or detached from the exact evaluation inputs.

ATTRACTOR already emphasizes deterministic adjudication, provenance, and SHA-256 digests. A future audit-log design should preserve that separation: the deterministic Judge remains the only authority for a verification verdict, while the audit log records evidence about the execution and supports independent integrity checks. A log record must not become a second source of truth for the verdict.

## Problem statement

Define a verifiable, versioned audit-event format that can detect accidental or deliberate modification, deletion, insertion, or reordering of records within the retained chain, while minimizing the amount of sensitive information stored in the log.

A hash chain can make changes detectable when a trusted checkpoint is retained. It cannot, by itself, prove that an event was truthful, that no event was omitted before the checkpoint, or that the checkpoint was not replaced by an attacker who controls the entire store.

## Proposed direction

Adopt a versioned, canonical audit-event envelope and link each event to the previous event digest. Each event would include, at minimum:

- schema and canonicalization version;
- a unique event identifier and a request/trace correlation identifier;
- event type and a UTC timestamp, explicitly treated as metadata rather than independent proof;
- the ATTRACTOR release or source revision and the version identifiers for the applicable verification protocol and rules;
- references and SHA-256 digests for the exact input/evidence artifacts that may lawfully be retained;
- the deterministic result identifier or digest, without redefining or recalculating the Judge's verdict;
- the previous event digest, plus the digest of the canonical event envelope.

The canonicalization algorithm and hash preimage must be fully specified and versioned. Digest fields must be excluded from their own preimage. Serialization must be deterministic across supported runtimes, with explicit handling for text encoding, key ordering, numbers, nulls, and Unicode. A verifier must be able to recompute every event digest and walk the chain without invoking an LLM or changing a historical verdict.

A future implementation should expose a verification report that distinguishes at least: valid chain, invalid digest/link, missing predecessor, unsupported schema/canonicalization version, and incomplete evidence. It must not silently repair or rewrite a broken historical chain.

## Data minimization and security

The audit log should retain only what is necessary to reproduce or verify the recorded operation. It must not indiscriminately copy request bodies, full documents, claims, excerpts, API keys, Authorization headers, secrets, or other sensitive payloads into operational logs. Where the audit process needs content, prefer access-controlled artifact references and cryptographic digests, with retention and access rules defined separately.

Hashing is not anonymization. Low-entropy or predictable source content may be guessable from a digest, and identifiers can still be personal data. The implementation design must include a data-classification and retention review, access control, backup protection, and documented deletion/legal-retention behavior.

For meaningful tamper evidence, checkpoints must be anchored outside the trust boundary of the writable event store. Candidate mechanisms include separately controlled immutable storage or externally signed checkpoints. The exact anchoring and key-management approach is intentionally not selected by this proposal.

## Alternatives considered

1. **Ordinary structured logs only.** Simple to operate, but do not provide an integrity link between records or an independent verification procedure.
2. **Independent hashes per event.** Detect changes only when the expected digest is retained in a separate trusted location; do not directly detect deletion or reordering of the event sequence.
3. **Hash-linked event chain.** Makes edits, insertion, and reordering detectable relative to a trusted checkpoint; selected as the proposed direction, subject to checkpoint and threat-model design.
4. **Signed events from the first version.** Can strengthen origin/authenticity guarantees but introduces signing-key custody, rotation, compromise recovery, and verification-policy questions. Deferred until requirements and threat model are agreed.

## Consequences

### Potential benefits

- Independent, deterministic integrity checks over retained audit history.
- Clear distinction between an operational event, its evidence artifacts, and the Judge's factual authority.
- Versioned canonicalization and schema allow future readers to verify old records without changing their meaning.
- Better ability to detect corruption and to document the limits of the evidence.

### Costs and limitations

- Additional storage, canonicalization, versioning, retention, and verification complexity.
- A hash chain does not establish that an event was complete or truthful at creation time.
- Integrity depends on trusted checkpoints and protection of the storage and verification process.
- Privacy, access-control, retention, and key-management decisions remain necessary.

## Acceptance criteria for a future implementation

Before implementation is proposed, a separate implementation plan should specify:

1. a threat model and trust boundaries, including checkpoint custody;
2. a canonical event schema and hash preimage with versioned test vectors;
3. deterministic verification tests for modification, deletion, insertion, reordering, truncation, and unsupported versions;
4. behavior for incomplete chains and corrupted records, without silent repair;
5. data minimization, access controls, retention, and privacy review;
6. a migration and compatibility plan for historical audit records;
7. independent review and reproducibility evidence.

## Explicit non-decision

This document is **Proposed**, not Accepted. It does not authorize code changes, database migrations, new dependencies, changes to Judge behavior, changes to frozen artifacts, or claims that the current audit store is tamper-proof. Any implementation requires a separate reviewed change and an explicit decision by the project owner.
