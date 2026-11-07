# Provenance — LLM-AggreFact TEST, RuleStanceDetector baseline (2026-11-06)

The two files in this directory are stored **byte for byte** as produced by the
GitHub Actions artifact `international-benchmark-aggregate-only` of run
[42276765499](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/42276765499)
(workflow `international-benchmark-manual.yml`, head `5f79290c5cdc32fb1d5be38a73dbc75167d246e3`,
conclusion `success`, dispatched and approved by the maintainer on 2026-11-06).

| File | SHA-256 |
| --- | --- |
| `aggregate.json` | `10778669be6c91472f68e7cd81f6534d8e915fbe718a2936030b962f92aadb4b` |
| `aggregate.md` | `f797aa55f170663c5e34a60951943209e11fece8b470a17c43ce044821268114` |

Scope and limits:

- Measures **only** `RuleStanceDetector` in isolation, without Judge 2.0. It is **not** the
  accuracy of the ATTRACTOR pipeline.
- Aggregate metrics only: no document text, claim or per-instance prediction is included.
- This is a negative baseline (balanced accuracy 0.4918, 95% bootstrap CI 0.4854–0.4982,
  n = 29,320). The TEST split is used for measurement only and never guides calibration,
  thresholds or method selection.
- Dataset: `lytang/LLM-AggreFact`, revision `981dfd0bd8e58e7238a9ab92b2e6ea44bce918e4`,
  file `data/test-00000-of-00001.parquet`, SHA-256
  `ba6976c3da990a9d7b11670efaf4e3c93c1bd0530061ec742afd6b2d5bce698c`
  (see `configs/benchmarks/llm-aggrefact-pin.json`). Used for evaluation only, under the
  dataset's access terms.
