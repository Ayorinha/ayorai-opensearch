# ADR-010: Verifiable audit log

- **Status:** Accepted in part — owner decisions 1–4 recorded on 2026-10-17; decisions 5–7 remain open
- **Date:** 2026-10-17
- **Decision owner:** Anderson Leon Ayora
- **Scope:** Design direction for a verifiable audit log. Implementation proceeds only through separate, reviewed PRs (see "Implementation phasing").

## Context

An auditable verification system needs to explain what was evaluated, which versioned rules produced the result, and whether the retained record has changed since it was created. Two gaps exist today (main `96cc965`):

- **R1 — audit store is not tamper-evident.** `AuditTraceStore.verify` recomputes a digest from the row itself; a writer with database access can change a row and its digest together, or delete it, without detection (reproduced 2026-10-17 with a throwaway test). PR #217 removed silent overwrite of duplicate `trace_id`s and documents this limit; it does not add tamper evidence.
- **R2 — verdicts are not recorded.** `/v1/verify` returns `input_sha256`, `output_sha256` and `rules_sha256` to the caller, but nothing is persisted server-side. ADR-009 §15 does not specify persistence, so this is a contract gap, not an implementation bug.

The deterministic Judge remains the only authority for a verdict. The audit log records evidence *about* an execution and must never become a second source of truth for the verdict.

## Requirements

1. Detect modification, deletion, insertion and reordering of recorded events.
2. Let a third party verify one event without the whole log and without the original server.
3. Detect a rewrite by an operator who controls the application, database, backups and signing key — to the extent that some state has been held outside that operator's control.
4. Store no claim text, excerpt, source text, request body, API key or personal data in the immutable log, including in the form of a guessable digest.
5. Allow erasure of the restricted data behind an event (LGPD) without breaking the log.
6. Use existing open specifications and maintained cryptographic libraries; no home-grown protocol or cryptography.

## Proposed direction

### Log structure

A Merkle-tree transparency log in the **C2SP tlog-tiles** format (v1.0.0): RFC 6962 tree hashing with SHA-256, 256-hash tiles, length-prefixed entry bundles. Each state is published as a **C2SP tlog-checkpoint** (v1.1.0) signed note: origin, tree size, base64 root hash.

A plain hash chain (each event links to the previous digest) was the first draft of this ADR. It is rejected as the primary structure because (a) proving one event requires the whole chain, while a Merkle inclusion proof needs about log₂(n) hashes, and (b) proving that the log only grew between two states requires the whole chain, while a Merkle consistency proof is compact. Neither structure, on its own, resists an operator who controls all copies; that property comes only from external state (below).

### Cryptographic profile

| Element | Choice | Basis |
| --- | --- | --- |
| Tree and leaves | RFC 6962, SHA-256 | C2SP tlog-tiles v1.0.0 |
| Log signature on checkpoints | Ed25519 (signed-note type 0x01), key name = log origin | C2SP tlog-checkpoint v1.1.0 |
| Witness cosignatures | ML-DSA-44 (type 0x06) recommended; Ed25519 (0x04) accepted | C2SP tlog-checkpoint / tlog-witness v1.1.0 |
| Post-quantum migration of the log key | Dual-sign the same checkpoint during transition | C2SP signed-note v1.1.0 (multiple signatures per note) |
| Library | `cryptography` (ML-DSA since 47.0.0; OpenSSL ≥ 3.5 since 48.0.0) | Official changelog |
| Canonical serialization | RFC 8785, as already used by the Judge | RFC 8785 |

### Leaf content and privacy

Because the Judge is deterministic, anyone who guesses an input can compute its output; direct `input_sha256`/`output_sha256` values in a permanent public log are therefore exposed to dictionary attacks when inputs are short or predictable. The leaf contains only:

- event schema version;
- `rules_sha256` and `software_id` (package version and artifact digest);
- a **salted commitment** `SHA-256(domain_label || salt || canonical_record)`, where `salt` is 32 random bytes per event and `canonical_record` (RFC 8785) holds `input_sha256`, `output_sha256`, `decision_state`, `verdict`, a pseudonymous client identifier and the server receive time (`time_source = "server_clock"`, explicitly untrusted).

The salt and canonical record are stored in an access-controlled, erasable store and are returned to the client in its receipt. Erasing them makes the commitment unlinkable while the tree stays valid. Consequence for the owner's decision: a third party can verify a specific event only if the client or the controller discloses its salt and record.

`verdict` is **not** published in clear in the leaf; it exists only inside the commitment (owner decision 2). A digest is not automatically non-personal data; classification remains a legal assessment.

### Proof objects (distinct, not interchangeable)

| Object | Contains | Proves | Does not prove |
| --- | --- | --- | --- |
| Submission receipt | index, leaf hash, origin, log signature | the log accepted the event at that index | inclusion in a tree |
| Inclusion proof (`c2sp.org/tlog-proof`, still a development version) | index, audit path, checkpoint | the leaf is in the tree of that checkpoint | that others see the same tree |
| Cosigned checkpoint | size, root, log and witness signatures | independent witnesses saw a consistent tree | wall-clock time |
| RFC 3161 timestamp (ICP-Brasil ACT, later phase) | checkpoint hash, time, ACT signature | the checkpoint existed at that time per the ACT policy | that a verdict is correct; authorship; creation date |

Given ATTRACTOR's low request volume, the proposal is to integrate each event into the tree **before** responding, so the client receives an inclusion proof rather than a promise. The latency cost is a hypothesis to measure.

### Recording `/v1/verify` (R2)

Every `/v1/verify` decision produces one event. In a "recording required" mode (pilot and organizational deployments), a failure to record returns an error and no verdict, so no verdict circulates unrecorded; in local mode the response states `audit_status = "not_recorded"`. Retries use an `Idempotency-Key` (same key and same input → same event and receipt; same key, different input → conflict). Concurrency is serialized by a single writer. These add fields to the `r2-a` response and therefore require an amendment to ADR-009 §15 and an OpenAPI change approved by the owner; `r1-a` is unchanged.

### External state (what actually defends against the operator)

Options, not mutually exclusive: client-held receipts; cosignatures from independent witnesses (C2SP tlog-witness); periodic RFC 3161 timestamps of checkpoints from an ICP-Brasil-accredited ACT; publishing checkpoint hashes to Sigstore Rekor (which accepts only hashedrekord and DSSE entries). Anchoring is per period on checkpoints, never per event (cost and timing privacy).

### Legacy records

The current `audit_traces` table is frozen as legacy. A digest of an exported, canonical snapshot enters the new log as its first leaf. An anchor made today proves the snapshot existed **from that date**; it does not prove the historical dates of the legacy events, and reports must say so.

## Guarantees and limits

- With no state outside the operator's control, **no guarantee** exists against an operator who controls application, database, backups and signing key.
- Rewrites of history before the latest external anchor are detectable by whoever holds that anchor; events after it remain exposed until the next anchor.
- Receipts do not prevent all omission: omission becomes detectable only for clients that kept a receipt or a later checkpoint.
- Integrity evidence does not establish that an input was truthful or that a verdict is correct.

## Alternatives considered

1. **Ordinary structured logs only** — no integrity link or independent verification.
2. **Independent hash per event** — detects edits only against a separately stored expected digest; not deletion or reordering.
3. **Hash chain** — detects edits relative to a trusted checkpoint, but proofs need the whole chain; superseded by option 5.
4. **HMAC with a server secret instead of salted commitments** — resists guessing, but only the secret holder can verify, and a leaked secret exposes every event.
5. **Merkle log in C2SP tlog-tiles format** — proposed.
6. **Implementation route for option 5:** (a) Python writer, with proofs cross-verified in CI by the Go reference tooling; (b) Trillian Tessera (Go, Apache 2.0, production-ready per its repository) run as a separate service. To be decided by an isolated proof of concept, not by preference.

## Acceptance criteria for a future implementation

1. Threat model and trust boundaries, including checkpoint and key custody.
2. Versioned event schema and commitment preimage with published test vectors.
3. Mutation tests on synthetic logs: every modification, deletion, insertion, reordering and truncation in the test plan is detected; inconsistent checkpoints and wrong keys are rejected.
4. Proofs produced by the implementation verify with an independent implementation.
5. Defined behavior for record failure, retry, concurrency and restart, without silent repair.
6. Data minimization, access control, retention and erasure reviewed.
7. Backup, restore and recovery tested against the last anchored checkpoint.
8. Measured latency and storage overhead on documented hardware.

## Owner decisions (recorded 2026-10-17)

| # | Question | Decision |
| --- | --- | --- |
| 1 | Salted commitments versus direct digests | **Salted commitments.** Leaves carry `SHA-256(domain_label \|\| salt \|\| canonical_record)`; salt and record live in an erasable, access-controlled store and in the client's receipt. Third-party verification of a specific event requires disclosure by the client or the controller. |
| 2 | Verdict in clear in the leaf | **No.** The verdict exists only inside the commitment. No public per-event or aggregate verdict statistics are derived from the log. |
| 3 | Behavior when recording fails in recording-required deployments | **Fail closed.** No verdict is returned without a recorded event; the API returns an error and the client may retry with the same `Idempotency-Key`. Local (non-recording) mode keeps `audit_status = "not_recorded"`. |
| 4 | Amendment to ADR-009 §15 | **Approved.** Recorded as ADR-009 §15.1: additive response fields outside `result`, only when recording is enabled; Judge rules, `result` and its hashes are unchanged. |

## Still open

5. Python writer versus Tessera, to be settled by proof of concept.
6. Who could act as independent witnesses.
7. Whether and when to procure ICP-Brasil timestamps.

## Implementation phasing

Each phase is a separate PR with its own review and CI evidence.

1. **Core library.** RFC 6962 Merkle tree hashing, inclusion and consistency proofs, and the salted commitment, as a pure library with published test vectors and cross-checks against independent implementations. No API, storage, dependency or Judge change.
2. **Checkpoints and storage.** C2SP checkpoint and signed-note (Ed25519), tile storage, single-writer append and restart behavior, mutation tests (acceptance criteria 3, 5 and 7). New runtime dependencies, if any, are declared and approved in that PR.
3. **Recording `/v1/verify`.** Recording-required mode, receipts, `Idempotency-Key`, OpenAPI change, per ADR-009 §15.1.
4. **External state.** Witnesses, RFC 3161 timestamps and anchoring, after decisions 5–7.

## Primary sources (consulted 2026-10-17)

C2SP: [tlog-tiles](https://c2sp.org/tlog-tiles), [tlog-checkpoint](https://c2sp.org/tlog-checkpoint), [signed-note](https://c2sp.org/signed-note), [tlog-cosignature](https://c2sp.org/tlog-cosignature), [tlog-witness](https://c2sp.org/tlog-witness), [tlog-proof](https://c2sp.org/tlog-proof). [RFC 6962](https://datatracker.ietf.org/doc/html/rfc6962), [RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785), [Tessera](https://github.com/transparency-dev/tessera), [Rekor v2 GA](https://blog.sigstore.dev/rekor-v2-ga/), [cryptography changelog](https://cryptography.io/changelog.html), [ITI — carimbo do tempo](https://www.gov.br/iti/pt-br/acesso-a-informacao/perguntas-frequentes/carimbo-do-tempo).

## Explicit non-decision

Accepting decisions 1–4 does not by itself change code, migrate databases, add dependencies, alter Judge behavior or frozen artifacts, or make the current audit store tamper-proof. Until phase 3 is merged and deployed, no deployment may be described as having a verifiable audit log.
