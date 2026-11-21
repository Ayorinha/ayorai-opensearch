# Audit-log test vectors (ADR-010, phase 1)

## `rfc6962-transparency-dev.json`

Generated with the Go reference implementation
[transparency-dev/merkle](https://github.com/transparency-dev/merkle)
(Apache-2.0), commit `c39fbf350a405f68571bf4c42a6a518eb0a46a4b`, Go 1.24.7,
by the program in `genvectors.go.txt` (placed at `cmd/genvectors/` inside that
repository and run with `go run ./cmd/genvectors`).

- 17 leaves: the 8 leaf inputs of `testonly.LeafInputs()` followed by
  `ayorai-vector-leaf-08` … `ayorai-vector-leaf-16` (UTF-8).
- `roots[s]`: tree head for every size 0–17; sizes 0–8 equal the published
  `testonly.RootHashes()` constants.
- Every inclusion proof `(index, size)` with `0 <= index < size <= 17` and
  every consistency proof `(size1, size2)` with `1 <= size1 <= size2 <= 17`.

The Python implementation must reproduce every value byte for byte; it is never
used to generate this file.

## `commitment-v1.json`

Expected commitments computed with coreutils `sha256sum` over a preimage
assembled by hand in the shell (`DOMAIN_LABEL || salt || RFC 8785 record`),
independently of `ayorai_attractor.auditlog.commitment`.

## `verify_receipts.go.txt` and `make_receipts_input.py` (ADR-010, criterion 4)

Cross-verification of the verify log (phases 2 and 3) with independent Go code:
signed notes with `golang.org/x/mod/sumdb/note` v0.43.0 and inclusion and
consistency proofs with `transparency-dev/merkle` at the commit above, Go 1.26.0.

1. `python tests/auditlog/vectors/make_receipts_input.py > receipts.json` writes 13
   receipts, an erasure of event 2 (leaf 13) and the consistency proof from
   size 5 to size 14. The seed is a fixed test value, never a production key.
2. Copy `verify_receipts.go.txt` to `main.go` in an empty Go module that
   requires both libraries, then run `go run . < receipts.json`.

Result on 2026-11-21: `receipts verified: 13/13; consistency 5->14: OK`.
Negative controls fail as expected:
- one zeroed node in an inclusion proof → `FAIL inclusion 3`;
- one altered checkpoint size → `FAIL checkpoint 0 invalid signature`;
- one node removed from the consistency proof → `consistency 5->14: FAIL`.

The Go program is stored as `.txt` so it does not join the Python build or the
repository's Go tooling.
