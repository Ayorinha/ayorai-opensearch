# ADR-010 persistence proof of concept

**Status:** experimental, isolated, not production code  
**Date:** 2026-11-21  
**Decision owner:** Anderson Leon Ayora

## Purpose

This directory contains a deliberately small SQLite writer prototype to test the persistence boundary that follows the existing ADR-010 Merkle core.

It accepts already-computed 32-byte RFC 6962 leaf hashes. It does not create or store claim records, salts, personal data, verdicts, API keys, or request bodies.

## What it exercises

- SQLite file-backed storage with WAL and FULL synchronous mode.
- One append transaction guarded by BEGIN IMMEDIATE.
- Two Python writer variants: a simple full-recompute baseline and an incremental Merkle-frontier writer.
- Contiguous append indices and structural checks on restart.
- Idempotent retry: same key and same leaf returns the original local receipt.
- Conflict: same key with a different leaf is rejected.
- Inclusion proof verification against the root captured when the entry was appended.
- Concurrent writer calls using independent SQLite connections.
- Process exit before commit and retry after commit when the original response is lost.
- Durable outbox state machine: PENDING → ASSIGNED → RECORDED, with unresolved-row recovery, immutable checkpoint receipts and unique Tessera index assignment.
- Detection of a changed leaf against a caller-held checkpoint.
- Detection of a deleted row without automatic repair.

## Run

From the repository root, after installing the development extra:

    python -m pytest tests/auditlog_poc -q

The Python tests reuse the public Go-generated Merkle vectors already checked
by tests/auditlog/test_merkle_vectors.py. The outbox tests simulate process exits
between local reservation, Tessera index assignment and checkpoint recording.
No new benchmark cases or business data are introduced.

To run the Tessera conformance experiments (Go 1.24+, OpenSSL 3+ and network
access to download pinned Go modules are required):

    python experiments/adr010_poc/run_tessera_poc.py
    python experiments/adr010_poc/run_tessera_http_poc.py

The first runs the upstream Tessera v1.0.4 POSIX one-shot personality and fsck
against the same 17 public vector leaves. The second starts the upstream POSIX
HTTP conformance personality on loopback, POSTs five public vector leaves,
checks assigned indices and the published checkpoint, then tests duplicate
behavior before and after a server restart. The in-memory antispam returns index
0 for an immediate duplicate, but after restart the same body/key is appended
again at index 5; a different body with the same Idempotency-Key is accepted at
index 6. This is a negative control proving that this conformance personality's
antispam is not durable idempotency. It is an upstream example only: it has no
AYORAI API-key authentication, no strict Idempotency-Key contract and no
/v1/verify integration.
Both scripts generate disposable Ed25519 signing keys with OpenSSL at runtime;
private keys are not committed and are deleted with the temporary directories.

## Deliberate limitations

This is not an implementation of the ADR-010 production phases.

- python_writer.py recomputes the entire Merkle root for every append: O(n) per append and O(n²) over n appends. It is a deliberately simple transaction/idempotency baseline.
- frontier_writer.py maintains the RFC 6962 compact frontier and updates O(log n) nodes per append. It rebuilds and validates the frontier on startup in O(n), and proof generation reads the selected leaf prefix. This is a more realistic Python candidate, but it is still an unsigned local SQLite prototype.
- It does not sign checkpoints or implement C2SP signed notes.
- It does not serve tlog-tiles, tile bundles, consistency proofs over HTTP, or witness cosignatures.
- It does not implement event schema, RFC 8785 commitment creation, salt custody, erasure, a complete HTTP idempotency adapter, or integration with /v1/verify.
- The outbox is a state-machine prototype only: the caller must verify the checkpoint signature before recording it and must reconcile PENDING rows by searching Tessera's durable log rather than blindly appending again.
- The outbox stores the raw Idempotency-Key in its experimental SQLite database; production must define key confidentiality, hashing/HMAC, retention and access control.
- It does not defend against an operator who can rewrite the database and every local copy of a checkpoint.
- A TreeHead or AppendReceipt from this prototype is unsigned and is not a trust anchor.

A successful test run proves only the tested SQLite mechanics and vector compatibility. It does not prove production readiness, tamper resistance, LGPD compliance, or an externally verifiable audit log. Neither Python writer has been benchmarked at scale.

## Next comparison

The Python writer and outbox prototypes are the baseline for a separate Tessera adapter experiment. The comparison must use the same public leaf vector, the same POSIX storage class, the same append/restart/concurrency workload, and documented hardware. It must report latency distributions, throughput, CPU, memory, storage growth, proof interoperability, restart behavior, and failure recovery.

Tessera itself is a Go library; the upstream project also provides POSIX conformance and one-shot personalities. A Python deployment would still need a small Go adapter/process boundary or a deliberate Go integration for AYORAI-specific authentication, strict idempotency and receipt semantics. That boundary and its operational cost must be included in the comparison.

No architecture choice is made here. ADR-010 owner decision 5 remains open.
