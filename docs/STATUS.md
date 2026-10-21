# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-21

This file is the single source of current project status. Historical documents describe the SHA they audited and must not be treated as a live status dashboard.

Historical snapshots and the previous execution-cycle merge table are preserved in [docs/history/STATUS-SNAPSHOTS.md](history/STATUS-SNAPSHOTS.md).

## API contract note (2026-10-21) — r1-a JSON null

The frozen contract remains HTTP 422 with error type `missing` and location `["body"]`; the fixture `tests/fixtures/r1-a-error-baseline.json` was not modified. The controlled isolated reproduction in [`scripts/repro_null_body_contract.py`](../scripts/repro_null_body_contract.py) tested 16 FastAPI/Pydantic combinations: FastAPI `0.115.0, 0.117.0, 0.119.0, 0.121.0, 0.123.0, 0.125.0, 0.127.0, 0.128.2`, each paired with Pydantic `2.10.0` and `2.13.5`, plus `httpx==0.27.2`. Both synthetic route styles reflecting the v0.4.0 typed-body route and v0.5.0 Any/Body + manual validation route returned 422 `missing`; direct `model_validate(None, from_attributes=True)` returned `model_attributes_type` in both tested Pydantic versions. No version threshold was identified; no dependency bound was added. Exact commands are recorded in CHANGELOG.md and the workflow from PR #339. This reproduces the relevant route styles in isolation rather than importing the tagged application, and does not establish behavior outside the tested matrix.

**Nota corretiva (2026-10-21):** a matriz inicial acima foi ampliada depois. A varredura controlada de FastAPI `0.128.2`–`0.157.0` com Pydantic `2.14.1` encontrou a primeira mudança do estilo tipado entre `0.150.0` (`missing`) e `0.151.0` (`model_attributes_type`); o estilo v0.5.0, com tratamento explícito de JSON `null`, preservou `422 missing` em todas as versões testadas. A varredura Pydantic `2.10.0`, `2.13.5`, `2.14.0` e `2.14.1` com FastAPI `0.157.0` confirmou o contraste. Não se alteraram API, fixture nem limites de dependência. Consulte a nota final datada no `CHANGELOG.md`.

## Current execution snapshot (2026-10-21)

- **Main snapshot SHA before this status-only update:** `7cf0d9ecb771712c8a9edd5351eaa47a79f33245`.
- **CI run:** [GitHub Actions run 39606736766](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39606736766). Main SHA had 13 checks: 12 successful, 1 skipped by workflow condition (`rgc-design-simulation`), 0 failures. Python test jobs 3.11, 3.12 and 3.13 passed.
- **Test evidence:** `pytest -q` — 1,123 passed, 1 skipped; coverage — 4,214 statements, 251 missed, 94%. The targeted additions brought `plugins/registry.py` to 26/26 statements and `providers/openai_compatible.py` to 30/30 statements.
- **Strict typing:** CI gate now runs `mypy --strict evals/ptbr/rgc_eval.py evals/ptbr/rgc_agreement.py`; the blocking gate passed on PR #353. Main's `typecheck-strict (non-blocking)` also passed.
- **Security:** [security run 39606736914](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39606736914) succeeded; `pip-audit` reported no known vulnerabilities and Bandit reported no issues. Remaining Bandit comment-parser warnings were removed in PR #354.
- **Merged work in this cycle:** #306 (manual 05), #308 (manual 06), #309 (manual 07), #335/#337 (DEC-017), #339 (JSON-null reproduction), #342 (DEC-018), #345 (manual 08), #349 (DEC-019), #351 (DEC-020), #352 (methodology review), #353 (coverage and strict mypy), #354 (Bandit warning cleanup), #355 (manual 09), #356 (manual 10), #357 (Unreleased/release draft), #358 (branch-cleanup audit).
- **Closed as duplicate/superseded:** #307, #328, #330, #334, #336, #338, #340, #343, #344, #346, #348, #350. Comments identify the replacement PRs.
- **Open PRs at snapshot time:** none.

**Nota de atualização (2026-10-21):** o bloco de snapshot acima é histórico, não o estado atual. A PR #369 foi mesclada (`1e77df724d432b05d230b112afd3ca6ff83eb3b0`) e adicionou o teste `tests/test_rgc_decision_consistency.py`. A PR #367 foi fechada sem merge por base desatualizada; a substituta #372 reaplica as justificativas `nosec` sobre a main atual e aguarda os checks obrigatórios.
- **Branch cleanup:** 205 remote branches were enumerated; 147 existing branches associated with merged PRs or explicitly superseded/duplicate PRs were listed as candidates. **Zero branches were deleted** because the available GitHub integration has no remote branch-delete operation. See [branch cleanup audit](audit/BRANCH-CLEANUP-2026-10-21.md).
- **Scientific boundary:** DEC-017, DEC-018, DEC-019 and DEC-020 are approved; the RGC protocol remains `[PROPOSTO]` and is not frozen. No pilot/benchmark cases were created, completed or labeled, and the ATTRACTOR was not run on RGC cases. No RGC metrics were produced.

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

- Manual chapters 05–10 are linked in `docs/manual/README.md`; chapters 01–04 remain marked in drafting.

**Nota corretiva (2026-10-21):** a afirmação sobre os capítulos 01–04 está superada: `docs/manual/01-visao-geral.md`, `02-arquitetura.md`, `03-judge.md` e `04-api.md` indicam `Estado: Atual`. O status de elaboração não se aplica a esses quatro capítulos.
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
