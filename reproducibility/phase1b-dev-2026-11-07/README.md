# Phase 1b DEV historical environment (2026-11-07/08)

`MANIFEST.json` records the exact environment (runner image, Python, every package
version) of the historical Phase 1b DEV runs. It is byte-identical to the copy on the
preserved branch `repro/phase1b-dev-env-2026-11-12` (head `0edc35b97ea6cd69d2b3e1258db355d7b31eb6a7`),
SHA-256 `3b23d698b971c19e3021167fbaa88b45cb0e98edc120f1d97f2df398e449ee3b`.

The three hash locks listed in `MANIFEST.json` stay on that branch, unchanged, and are
not installed by any workflow. They are not copied here because they pin packages with
published advisories (nltk 3.9.4, cryptography 46.0.3) that the dependency review gate
rejects. Their SHA-256, also recorded in `docs/audit/PR-INVENTORY-2026-11-20.md`:

| file | SHA-256 |
|---|---|
| `inference-requirements.lock.txt` | `cf052d1fb0c78a688349476b71ebd4b0856419945ba07b2d74997f2220347000` |
| `aggregate-requirements.lock.txt` | `64e8244f7b0ae7a6abceef63840492f2cb5b8cb73dede1bb99696301a71ab908` |
| `aggregate-minimal-requirements.lock.txt` | `a3d9cbf29d29ea358b59e03268a4fcb5bc169978835d190fee19f0299abd378c` |

Retrieve one with `git show 0edc35b9:reproducibility/phase1b-dev-2026-11-07/<file>`.

The current inference environment (`requirements-phase1b-inference.txt` and
`requirements-phase1b-torch-cpu.txt`) keeps these versions and hashes, with
cryptography 50.0.2 and the nltk 3.9.4 segmentation vendored in
`scripts/benchmarks/phase1b/vendor_nltk/` instead of the nltk package.
