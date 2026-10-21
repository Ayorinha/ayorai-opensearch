# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-21

This file is the single source of current project status. Historical documents describe the SHA they audited and must not be treated as a live status dashboard.

Historical snapshots and the previous execution-cycle merge table are preserved in [docs/history/STATUS-SNAPSHOTS.md](history/STATUS-SNAPSHOTS.md).

## API contract note (2026-10-21) — r1-a JSON null

The frozen contract remains HTTP 422 with error type `missing` and location `["body"]`; the fixture `tests/fixtures/r1-a-error-baseline.json` was not modified. The controlled isolated reproduction in [`scripts/repro_null_body_contract.py`](../scripts/repro_null_body_contract.py) tested 16 FastAPI/Pydantic combinations: FastAPI `0.115.0, 0.117.0, 0.119.0, 0.121.0, 0.123.0, 0.125.0, 0.127.0, 0.128.2`, each paired with Pydantic `2.10.0` and `2.13.5`, plus `httpx==0.27.2`. Both synthetic route styles reflecting the v0.4.0 typed-body route and v0.5.0 Any/Body + manual validation route returned 422 `missing`; direct `model_validate(None, from_attributes=True)` returned `model_attributes_type` in both tested Pydantic versions. No version threshold was identified; no dependency bound was added. Exact commands are recorded in CHANGELOG.md and the workflow from PR #339. This reproduces the relevant route styles in isolation rather than importing the tagged application, and does not establish behavior outside the tested matrix.

**Correction dated 2026-10-21:** the paragraph above describes only the initial 16-combination matrix and is historical. The expanded controlled bisection found the first change in the typed-route style between FastAPI `0.150.0` (`missing`) and `0.151.0` (`model_attributes_type`); the v0.5.0 explicit `payload is None` guard preserves HTTP 422 `missing` through FastAPI `0.157.0` with Pydantic tested through `2.14.1`. No API, fixture or dependency bound changed; see the final bisection result in `CHANGELOG.md`.

## Current execution snapshot (2026-10-21)

- **Main snapshot SHA before this final status/release-only PR:** `daf9ce3771712f60ddce2ff76e7118d25fafb656`.
- **CI:** [run 39637737566](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39637737566) completed successfully on that SHA: 13 checks, 12 successful, 1 skipped by workflow condition (`rgc-design-simulation`), no failures. Python 3.11, 3.12 and 3.13 jobs passed.
- **Security and CodeQL:** [security run 39637737626](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39637737626) and [CodeQL run 39637737611](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39637737611) succeeded.
- **Test evidence:** the CI test jobs ran `pytest -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning --cov=ayorai_attractor --cov-report=xml --cov-report=json --cov-report=term-missing`: **1,126 passed, 1 skipped**; coverage **4,214 statements, 251 missed, 94%**. The namespace-compatibility job also ran `pytest -q` successfully.
- **Quality commands observed in CI:** `ruff check .`, `ruff format --check .`, and `mypy --strict evals/ptbr/rgc_eval.py evals/ptbr/rgc_agreement.py` all passed.
- **Merged PRs since the previous snapshot:** #369 (approved-amendment consistency test; merge SHA `1e77df724d432b05d230b112afd3ca6ff83eb3b0`), #370 (historical amendment consistency; merge SHA `7fc9ae9708ff8ee46ffe2398efa4d6024d36ce90`), #373 (Bandit `# nosec` rationales; merge SHA `fc12c38e5bc2967642d2bd941d01fc52b4f206fb`), #374 (status and v0.6.0 draft; merge SHA `a269d5f5371f3b2545635515d6b98d8cfe679ba6`), and #375 (consolidated amendment guard; merge SHA `daf9ce3771712f60ddce2ff76e7118d25fafb656`).
- **Closed without merge as superseded:** #367 and #372 were replaced by #373; #368 was replaced by #370; #371 was replaced by #374. The PR conversations record the replacements.
- **Open PRs at snapshot time:** this final status/release-only PR is the only remaining open PR; no other work PR is open. After it merges, no PR should remain open.
- **Branch cleanup:** no remote branches were deleted. The candidate audit remains in [the branch-cleanup audit](audit/BRANCH-CLEANUP-2026-10-21.md); actual deletion is deferred to the maintainer as instructed.
- **Scientific boundary:** DEC-017, DEC-018, DEC-019 and DEC-020 are approved. The RGC protocol remains `[PROPOSTO]` and is not frozen. No pilot/benchmark cases were created, completed or labeled; ATTRACTOR was not run on RGC cases and no RGC metrics were produced.

## Release and system boundaries

- Latest published release remains **v0.5.0** (Zenodo DOI [10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005)); all-versions DOI: [10.5281/zenodo.23125082](https://doi.org/10.5281/zenodo.23125082).
- A v0.6.0 notes draft exists at `docs/release/v0.6.0-draft.md`. No tag or release was created or published in this cycle.
- The RGC protocol remains `[PROPOSTO]`; approved decision options define rules but do not freeze the protocol or authorize a benchmark run.
- No claims of certification, institutional validation, independent review or production readiness are supported by the current evidence.

## Maintainer decisions and governance

- **DEC-017 — approved by the maintainer (2026-10-21), Option A:** a missing/integrity-invalid record interrupts; a present but invalid prediction counts as an error in the denominator. Implementation/doc alignment: PRs #335 and #337.
- **DEC-018 — approved by the maintainer (2026-10-21), Option A:** H1 is confirmatory only on the hidden partition (~90 cases); the ~210 public cases are descriptive/exploratory. Executor requires an explicit partition. PR #342.
- **DEC-019 — approved by the maintainer (2026-10-21), Option A:** article-cluster bootstrap is the primary 95% CI; case bootstrap is sensitivity. `bootstrap_cluster_id` is required for hidden cases, with canonical multi-article bundle rules. PR #349.
- **DEC-020 — approved by the maintainer (2026-10-21), Option A:** unweighted Cohen's kappa, point-estimate gate `κ ≥ 0.6`, case-bootstrap 95% CI, confusion matrix/class marginals, and auditable `RULE_GAP` exclusions. Calculator and guide are in PR #351.
- Other decisions remain as recorded in [DECISIONS-PENDING.md](DECISIONS-PENDING.md); do not infer approval from an implementation or CI result.
- **Protocol freeze:** not approved by these decisions. The protocol remains proposed; no definitive case set has been created.

## Schemathesis issue #250

Issue [#250](https://github.com/Ayorinha/ayorai-opensearch/issues/250) was closed after #259 corrected the asymmetric `negative_data_rejection` exclusion between `/v1/opensearch` and `/v1/audit`. It remains **under observation for recurrence**. The historical failing run and its falsifying case were not found; do not claim the historical failure was reproduced. PR #253 preserves logs, served OpenAPI, and Hypothesis examples for future failures.

## Next human step: RGC pilot 02

1. Conduct pilot 02 with human annotation only and without AI assistance; record methodological findings and discard pilot labels as required by the protocol.
2. Obtain a second annotation from a different person, independently of the first annotation. Only after both human annotation files exist should the agreement calculator be run; it has not processed real annotation data.
3. Complete the independent human review F-01.
4. Decide separately whether to freeze the protocol and whether the hidden partition's provenance/isolation gates are satisfied. No case creation, labeling, system execution or benchmark metrics are authorized before those gates.

## Deferred work

- Manual chapters 01–04 have `Estado: Atual`; chapters 05–10 are linked in `docs/manual/README.md`.
- Coverage is 94% overall. The next useful targets include `verification/extraction.py`, `audit.py`, and `orchestrator.py`; the registry and OpenAI-compatible provider now have 100% line coverage.
- Strict mypy now covers both RGC evaluation modules. Keep the scope evidence-driven and extend it only where the gate passes.
- Security CI is clean: pip-audit found no known vulnerabilities; Bandit found no issues after comment-parser warning cleanup.
- v0.6.0 notes remain a draft; do not create a tag or publish a release.
- Remote branch deletion remains blocked by missing connector capability. The audit records candidates but does not claim deletion.

## Engineering gates

- Frozen `rules/`, Judge 2.0, Golden files, manifests, hashes, RGC source captures, release artifacts, and preregistrations remain protected.
- The current access log is privacy-conscious operational evidence, not proof of tamper resistance.
- `/health` remains public; rate limiting and service-owned TLS are not implemented.
- Green checks are SHA-specific and do not substitute for independent human review.
- Do not claim benchmark results, legal compliance, production readiness, or institutional partnership without evidence.
