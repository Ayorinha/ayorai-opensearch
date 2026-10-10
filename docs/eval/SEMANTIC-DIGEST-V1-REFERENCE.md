# Semantic Digest v1 — Base-Commit Metric References

**Purpose:** preserve the existing evaluation metric outputs while adding `semantic_sha256`. These references are for regression checks, not new performance claims.

**Reference base commit:** `4f094a13bc566d6b6c856bf78d59fea3707cdd31` (main after PR #121, before PR 0.9). The semantic digest did not exist at this commit, so no semantic digest value is claimed for the base commit.

## Reproduction commands

At the reference commit, install the project and run:

```bash
git checkout 4f094a13bc566d6b6c856bf78d59fea3707cdd31
python -m pip install -e ".[dev]"
attractor eval --suite golden-v0 --out /tmp/golden-v0.json
attractor eval --suite golden-v0.1 --out /tmp/golden-v0.1.json
python - <<'PY'
import json
from pathlib import Path

for suite in ("golden-v0", "golden-v0.1"):
    report = json.loads(Path(f"/tmp/{suite}.json").read_text(encoding="utf-8"))
    print(suite, {
        "global_accuracy": report["global_accuracy"],
        "balanced_accuracy": report["balanced_accuracy"],
        "legacy_accuracy": report["legacy_accuracy"],
        "mcnemar_vs_legacy": report["mcnemar_vs_legacy"],
    })
PY
```

## Recorded output

These metric values were supplied from Cláudio's local execution of the base-commit code. The PR 0.9 tests and CI repeat the evaluations and assert the same values.

### Golden v0

- Cases: 34 total; 30 with global verdict.
- `global_accuracy`: 7/30 = `0.233333`.
- `balanced_accuracy`: `0.42735`.
- `legacy_accuracy`: 13/30 = `0.433333`.
- McNemar: `legacy_correct_new_wrong=10`, `new_correct_legacy_wrong=4`, exact p-value `0.1795654296875`.

### Golden v0.1

- Cases: 34 total; 30 with global verdict.
- `global_accuracy`: 10/30 = `0.333333`.
- `balanced_accuracy`: `0.481838`.
- `legacy_accuracy`: 13/30 = `0.433333`.
- McNemar: `legacy_correct_new_wrong=9`, `new_correct_legacy_wrong=6`, exact p-value `0.60723876953125`.

## Interpretation and invariants

- Do not change these expected values to make CI pass. If a value differs, investigate the implementation, suite inputs, or execution environment.
- Do not edit Golden v0/v0.1, the corpus, manifests, or historical reports as part of this change.
- The older narrative in [BASELINE-v0.md](BASELINE-v0.md) is a historical baseline report and must not be silently rewritten to these later code-version measurements.
- The legacy `content_sha256` keeps its existing calculation and report placement. It may change between equivalent runs because nested per-result latency remains included.
- `semantic_sha256` is versioned and its reference values are deliberately fixed in CI for Golden v0 (`21abb816facce73fc924842d12b373b8792abc2e7389e129c35bb58bab806632`), Golden v0.1 (`64f743b3e87553b2eca207cbb60a0ae8f87d619bc968c8ed562f8048f1529608`), and smoke-v0 (`969ec61a4aee4e4426f5d217819bd185ebba248743e7721714a3123f5df67c3d`). If an intentional change alters any reference digest, it requires a separate PR, an explicit rationale documenting the semantic change and its effect on case-level predictions, and maintainer approval. Do not update these values merely to make CI pass.
- A stable semantic digest is evidence that the canonicalized semantic report is unchanged; it is not, by itself, proof that every replay path or every external dependency is reproducible.
