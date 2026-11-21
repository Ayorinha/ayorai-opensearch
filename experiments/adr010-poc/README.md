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
- Contiguous append indices and structural checks on restart.
- Idempotent retry: same key and same leaf returns the original local receipt.
- Conflict: same key with a different leaf is rejected.
- Inclusion proof verification against the root captured when the entry was appended.
- Concurrent writer calls using independent SQLite connections.
- Detection of a changed leaf against a caller-held checkpoint.
- Detection of a deleted row without automatic repair.

## Run

From the repository root, after installing the development extra:

    python -m pytest tests/auditlog_poc -q

The tests reuse the public Go-generated Merkle vectors already checked by
tests/auditlog/test_merkle_vectors.py. No new benchmark cases or business data
are introduced.

## Deliberate limitations

This is not an implementation of the ADR-010 production phases.

- It recomputes the entire Merkle root for every append: O(n) per append and O(n²) over n appends. This is intentionally simple and unsuitable for a growing production log.
- It does not sign checkpoints or implement C2SP signed notes.
- It does not serve tlog-tiles, tile bundles, consistency proofs over HTTP, or witness cosignatures.
- It does not implement event schema, RFC 8785 commitment creation, salt custody, erasure, API idempotency, or integration with /v1/verify.
- It does not defend against an operator who can rewrite the database and every local copy of a checkpoint.
- A TreeHead or AppendReceipt from this prototype is unsigned and is not a trust anchor.

A successful test run proves only the tested SQLite mechanics and vector compatibility. It does not prove production readiness, tamper resistance, LGPD compliance, or an externally verifiable audit log.

## Next comparison

The Python prototype is the baseline for a separate Tessera adapter experiment. The comparison must use the same public leaf vector, the same POSIX storage class, the same append/restart/concurrency workload, and documented hardware. It must report latency distributions, throughput, CPU, memory, storage growth, proof interoperability, restart behavior, and failure recovery.

Tessera is a Go library, not a turnkey HTTP microservice. A Python deployment would need a small Go adapter/process boundary or a deliberate Go integration. That boundary and its operational cost must be included in the comparison.

No architecture choice is made here. ADR-010 owner decision 5 remains open.
