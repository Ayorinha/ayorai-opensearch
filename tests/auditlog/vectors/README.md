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
