# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-21

This file is the single source of current project status. Historical documents describe the SHA they audited and must not be treated as a live status dashboard.

## API contract note (2026-10-21) — r1-a JSON `null`

PR #274 restored the `/v1/verify` JSON `null` request-body response to the frozen contract fixture: HTTP 422 with error type `missing`, as captured in `tests/fixtures/r1-a-error-baseline.json` from commit `c7e3868f3f6f34ce153d9ec6605645fad8681e2e`. The fixture was not changed; `tests/test_verification_api.py` compares each case byte-for-byte. A report says tags v0.4.0 and v0.5.0, installed with today's dependency resolution, returned `model_attributes_type`. This is consistent with a dependency-version-dependent FastAPI/Pydantic validation difference, but that cause has not been isolated by a controlled reproduction. No API behavior is changed by this note.



## Current execution snapshot (2026-10-21)

- **Main SHA at this snapshot:** `e52af8388d3e8b5a6fa89a49e74ed469328cc231` ([commit](https://github.com/Ayorinha/ayorai-opensearch/commit/e52af8388d3e8b5a6fa89a49e74ed469328cc231)).
- **Latest CI evidence:** PR #291 head `39de4f38d7de58c3fd70c877a4a3c8f5b5c686a3` passed CI, including Python 3.11/3.12/3.13, `ruff check .`, `ruff format --check .`, `mypy --strict evals/ptbr/rgc_eval.py`, and `pytest -q`; CodeQL, Security, API Contract Guard, Schemathesis Full API Contract, Golden r2 Migration, and Dependency Review also passed. The RGC design simulation was skipped by its workflow condition; this is not a successful RGC simulation or benchmark evidence. These are checks on the PR head SHA, not a claim that a separate push-triggered run was observed on the resulting main merge SHA.
- **PR #284 — audit trail:** merged as `2ed5aca25c260f6c689c00747da2b22591e52813`; restores the pre-#274 wording of H1 and §§4–5 and adds a dated corrective note without rewriting history.
- **DEC-016:** recorded and merged in PR #286 (`d958474954c2215f90451130f95831a17cab56b9)); authorizes autonomous technical/documentary work subject to gates and limits. PRs #266 and #267 were retroactively ratified by the maintainer's order, without independent review. **F-01 remains open.**
- **RGC baseline:** Emenda 6 was merged in PR #288 (`5a587ecb64abc6359c8fe36b8194b67dee3edda9`). Baseline B is primary from human reference labels in the public 70% development partition; A is descriptive only; ties in B use the fixed `judge2` vocabulary order in `majority_label`. The protocol remains **[PROPOSTO]**, not frozen.
- **PR #277:** closed as superseded by Emenda 6. The comment now identifies the review as automated and not independent.
- **r1-a JSON `null`:** PR #289 records the frozen fixture expectation (`missing`) and the reported `model_attributes_type` behavior from v0.4.0/v0.5.0 under current dependency resolution as an unresolved dependency-version hypothesis. PR #291 adds a clearer regression-test message. Both the fixture and API behavior remain unchanged.
- **Open dependency update:** PR #282's CodeQL action update passed its checks on head `babc12722add0bfe40bf503501b91d3a6f0dbc11`, but its base is stale after recent merges. Rebase or recreate it from current `main`, then rerun checks before merging.
- **Human/scientific gates:** pilot 02 remains human-only; do not create, complete, or label pilot/benchmark cases, and do not execute ATTRACTOR on any RGC pilot/development/confirmatory cases. No RGC PT-BR benchmark result exists. Do not freeze the protocol until the human pilot 02 review and a separate explicit maintainer decision.
- **Review status:** this cycle's reviews are automated, not independent. Do not describe them as independent reviews or institutional validation.


## Execution snapshot before PR #280 merge (2026-10-20)

- `main` SHA immediately after PR #279 and before PR #280: `7a4a26805f70726fca63560d7ab05ae71207c4e2` ([commit](https://github.com/Ayorinha/ayorai-opensearch/commit/7a4a26805f70726fca63560d7ab05ae71207c4e2)). The connector returned no combined-status entries for this merge commit, so this page does not assert that its required checks passed; check the SHA-specific Actions runs before relying on main status.
- PR #273 merged the methodological review. Its findings are documented, but the RGC protocol remains **not frozen**.
- PR #274 merged the baseline-B implementation and also changed H1 and §§4–5 in `PREREGISTRATION-RGC-v1.md` without a dated approved amendment in that file. The corrective proposal in [PR #284](https://github.com/Ayorinha/ayorai-opensearch/pull/284) restores the pre-#274 wording and records the audit-trail gap; it does not alter the historical Git record or authorize execution. The discrepancy between the restored preregistration and Protocol Amendment 5 requires an explicit, dated maintainer decision.
- PR #275 clarified that `RULE_GAP` is an exploratory pilot-only marker, not a Judge verdict and not a metric/concordance label.
- PR #278 corrected H1 runner suite selection and strengthened report-manifest integrity checks; it does not establish benchmark performance.
- PR #279 clarified the statistics contract: legacy ADR-002 6×6 matrix versus RGC `judge2` vocabulary, and missing prediction records versus present `INVALID_PREDICTION` values.
- [PR #277](https://github.com/Ayorinha/ayorai-opensearch/pull/277) remains a Draft methodological proposal with a stale base SHA. Reconcile its base and re-review only after the preregistration correction is resolved. Do not merge it or treat it as execution authorization.

## Main SHA and checks

- **Main SHA immediately before the final status merge (#255):** `919ba7b4f7d13b57aa198508c32523c999393863`.
- On that SHA, the six required checks passed: Python 3.11, Python 3.12, Python 3.13, `golden-regression`, `judge-regression`, and `security`. The branch-scoped `rgc-design-simulation` job is intentionally skipped on main; the synthetic simulation passed separately on PR #241 SHA `0e515e9c76328c7023b24394459acc21d9e2bd0a` (GitHub Actions run [39091010493](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39091010493)).
- This is the base SHA for the final status PR. The squash commit for #255 advances `main`; its resulting SHA is the closing commit recorded in GitHub's merge history and in the final execution report.

## Release and system boundaries

- Latest release: v0.5.0 (2026-10-13), DOI [10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005).
- `main` is protected. Required checks are Python 3.11/3.12/3.13, `golden-regression`, `judge-regression`, and `security`.
- The deterministic Judge alone is the factual authority. Automated checks, LLM outputs, and synthetic simulations do not replace human review or establish benchmark performance.
- **No Portuguese benchmark result exists.** The exploratory pilot 01 was discarded; the system was not run on those cases. The RGC protocol is not frozen.

## PRs merged in this execution cycle

| PR | Change | Squash commit |
|---|---|---|
| [#258](https://github.com/Ayorinha/ayorai-opensearch/pull/258) | DEC-013: authorization and limits for this execution cycle | `22fece06c7a58b05e11e7ee1aa3aad6191969c36` |
| [#257](https://github.com/Ayorinha/ayorai-opensearch/pull/257) | Clarify verified agent runtime behavior | `6fbb58a1b16b5ee89f4117b8e37974c51baf18c5` |
| [#232](https://github.com/Ayorinha/ayorai-opensearch/pull/232) | RGC `rectified` stratum and validation | `b7a076f2fcaf05b50599b8416574636ca4eb1f63` |
| [#259](https://github.com/Ayorinha/ayorai-opensearch/pull/259) | Align Schemathesis legacy exclusion for `/v1/audit`; close issue #250 | `ec8b71be0d6e59ad93abd053a3df9d5ce0ea3c70` |
| [#260](https://github.com/Ayorinha/ayorai-opensearch/pull/260) | Structured privacy-safe access logs under Uvicorn | `2da10d557c7d884d87e4f6baa1c55be94a3b32d7` |
| [#261](https://github.com/Ayorinha/ayorai-opensearch/pull/261) | Automated relative Markdown link and anchor integrity | `3587248a9d0d981e5fb8b7d9a074ea250dbd08c2` |
| [#241](https://github.com/Ayorinha/ayorai-opensearch/pull/241) | DEC-014 and Protocol Amendment 5; synthetic power simulation | `d8411d90f8905442ac02568cc9179ce42afec69a` |
| [#242](https://github.com/Ayorinha/ayorai-opensearch/pull/242) | Reconcile technical audit and current findings | `919ba7b4f7d13b57aa198508c32523c999393863` |
| [#255](https://github.com/Ayorinha/ayorai-opensearch/pull/255) | Final reconciliation of this status page | This is the final merge of the cycle |
| [#284](https://github.com/Ayorinha/ayorai-opensearch/pull/284) | Restore RGC preregistration audit trail | `2ed5aca25c260f6c689c00747da2b22591e52813` |
| [#286](https://github.com/Ayorinha/ayorai-opensearch/pull/286) | Record maintainer authorization DEC-016 | `d958474954c2215f90451130f95831a17cab56b9` |
| [#288](https://github.com/Ayorinha/ayorai-opensearch/pull/288) | Incorporate RGC baseline B amendment 6 | `5a587ecb64abc6359c8fe36b8194b67dee3edda9` |
| [#289](https://github.com/Ayorinha/ayorai-opensearch/pull/289) | Record frozen r1-a null-body contract history | `d2ac6420599c2106a2f81715626a2f7924b54f3a` |
| [#291](https://github.com/Ayorinha/ayorai-opensearch/pull/291) | Clarify frozen r1-a null-body contract drift | `e52af8388d3e8b5a6fa89a49e74ed469328cc231` |

Supporting changes already on main: #252 sets API-key authentication fail-closed by default; #253 preserves Schemathesis evidence artifacts; #254 corrects DEC-012 status; #256 enforces `--lifespan on` at startup.

## Maintainer decisions and governance

- **DEC-013 (2026-10-18):** authorizes execution and merge of the defined PRs in this cycle. The waiver of independent human review applies only to this cycle; it does not mean a human independent review occurred. **F-01 remains open.**
- **DEC-014 (2026-10-18):** baseline B is primary, derived only from the public 70% development partition and fixed for confirmatory evaluation. Baseline A is a descriptive oracle baseline calculated on the evaluation partition; it is never an operational classifier or the basis for H1.
- **Emenda 6 (2026-10-21):** approved by the maintainer and merged in #288; it supersedes the earlier restriction on changing the preregistration while preserving the original text as history. It does not freeze the protocol.
- **DEC-016 (2026-10-21):** autonomous work authorization and retroactive ratification of PRs #266/#267; no independent review was performed for those PRs. F-01 remains open.
- **Protocol Amendment 5** records only the baseline definition. It does not freeze the RGC protocol.
- **Open maintainer decisions:** DEC-001 (lockfile/image digest), DEC-003 (ADR-001 status), DEC-004 (commercial documentation/repository name), DEC-006 (Portuguese stance-engine priority), renumbering DEC-007/DEC-008 or retaining qualifiers, and ADR-010 questions 5–7 (writer, witnesses, timestamp).
- **ADR-010:** “Accepted in part”; phase 1 is a pure library merged in #236. No event persistence, recording API, signed checkpoint service, or deployed verifiable audit log exists.

## Schemathesis issue #250

Issue [#250](https://github.com/Ayorinha/ayorai-opensearch/issues/250) was closed after #259 corrected the asymmetric `negative_data_rejection` exclusion between `/v1/opensearch` and `/v1/audit`. It remains **under observation for recurrence**. The historical failing run and its falsifying case were not found; do not claim the historical failure was reproduced. PR #253 preserves logs, served OpenAPI, and Hypothesis examples for future failures.

## Next human step: RGC pilot 02

Run the second small pilot with human annotation without AI assistance, record methodological findings, and discard the pilot labels. Review those findings before deciding separately whether to freeze the protocol. Only after that gate should the definitive 300-case set, second annotation, agreement check (Cohen's kappa >= 0.6), and single system run be prepared. **Do not create or execute benchmark cases now.** No PT-BR benchmark results exist.

## Deferred work

Waves 6, 7, 8, and 9 are postponed to the next technical-manual stage and were not executed in this cycle. The manual should distinguish implemented code, library-only functionality, proposed work, and unimplemented work, with a verifiable source for each claim.

## Engineering gates

- Frozen `rules/`, Judge 2.0, Golden files, manifests, hashes, RGC source captures, release artifacts, and preregistrations remain protected.
- The current access log is privacy-conscious operational evidence, not proof of tamper resistance.
- `/health` remains public; rate limiting and service-owned TLS are not implemented.
- Green checks are SHA-specific and do not substitute for independent human review.
- Do not claim benchmark results, legal compliance, production readiness, or institutional partnership without evidence.
