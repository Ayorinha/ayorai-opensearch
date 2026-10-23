# Historical STATUS snapshots

> **Aviso histórico — 2026-10-23:** este documento registra uma versão, auditoria, avaliação ou rascunho anterior; preserve-o como evidência histórica e não o trate como estado atual nem como resultado de benchmark vigente. Consulte docs/STATUS.md and docs/TRACEABILITY-MASTER.md.


Moved from `docs/STATUS.md` on 2026-10-21 to keep the live status page focused on the current snapshot. The sections below are preserved verbatim from main SHA `8664286e81593c36e7901c596a6aa01a00cd05cf`; historical claims are not current status.

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
