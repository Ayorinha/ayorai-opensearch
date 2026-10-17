# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-17

Status snapshot: `main` at `d4d76e98ce720a1208bfb34b762073c91ca940f4`. Check-run state is SHA-specific; consult the linked GitHub checks for the exact commit rather than inferring CI status from this page.

## Source of truth

This file is the **single source of current project status**: release state, active work, maturity labels and current blockers are maintained here only. The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) remains the canonical requirements-and-evidence matrix, but is not a second current-status dashboard. Other progress, milestone and institutional documents may preserve historical snapshots; current status must link back to this page.

## Current execution

- Latest release: v0.5.0 (2026-10-13), tag on main commit e9eccb5; version DOI 10.5281/zenodo.23344005.
- `main` is protected: pull request required, plus test (3.11), test (3.12), test (3.13), golden-regression, judge-regression and security.
- **DEC-010 is approved, option A (~one-third compound claims):** decision [PR #204](https://github.com/Ayorinha/ayorai-opensearch/pull/204); executor `rgc-eval/0.2.0`, including the `atoms` field, [PR #203](https://github.com/Ayorinha/ayorai-opensearch/pull/203); Protocol Amendment 3 [PR #205](https://github.com/Ayorinha/ayorai-opensearch/pull/205).
- **Exploratory 20-case pilot completed on 2026-10-16**, annotated by Anderson. Distribution: 9 SUPPORTED, 11 REFUTED, 0 UNVERIFIED, 0 PARTIALLY_SUPPORTED, 0 CONFLICTING and 0 RULE_GAP. The pilot did not include cases designed to exercise PARTIALLY_SUPPORTED or CONFLICTING. Pilot results are discarded; pilot labels are not in the repository. The system was not run on these cases, so this pilot does not measure system performance.
- **DEC-011 approved in full on 2026-10-17:** pilot findings in [PR #206](https://github.com/Ayorinha/ayorai-opensearch/pull/206) and [PR #207](https://github.com/Ayorinha/ayorai-opensearch/pull/207); Protocol Amendment 4 merged in [PR #227](https://github.com/Ayorinha/ayorai-opensearch/pull/227); status reconciliation in [PR #228](https://github.com/Ayorinha/ayorai-opensearch/pull/228) and [PR #229](https://github.com/Ayorinha/ayorai-opensearch/pull/229), which also adds the blank second-pilot worksheet `docs/eval/PILOT-RGC-02-WORKSHEET.md`.
- **Protocol not frozen.** The second human pilot (about 10 new cases, annotated without AI tools, discarded after review) has not been run. Freezing requires an explicit maintainer record after reviewing that pilot.
- **No Portuguese benchmark result exists.** The exploratory pilot is discarded and is not a system evaluation. Next steps: run the second human pilot; review findings; record the freeze decision; prepare 300 definitive cases; obtain a second annotator and require Cohen's kappa >= 0.6; then run the system once.
- **Verifiable audit log (ADR-010):** owner decisions 1–4 (DEC-012) were recorded and merged in [PR #225](https://github.com/Ayorinha/ayorai-opensearch/pull/225); the phase-1 pure Merkle/commitment library and vectors were merged in [PR #236](https://github.com/Ayorinha/ayorai-opensearch/pull/236). This is limited library functionality: no audit-log field, event storage, recording API, signed checkpoint service or deployed verifiable log exists. ADR-010 phases 2–4 remain future work.
- Earlier RGC preparation: [#176](https://github.com/Ayorinha/ayorai-opensearch/pull/176) records DEC-002; [#177](https://github.com/Ayorinha/ayorai-opensearch/pull/177) addresses official source capture and SHA-256; [#178](https://github.com/Ayorinha/ayorai-opensearch/pull/178) documents derived text; [#179](https://github.com/Ayorinha/ayorai-opensearch/pull/179) proposes the executor; [#192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) addresses canonical URL serialization; [#193](https://github.com/Ayorinha/ayorai-opensearch/pull/193) contains Amendment 2; [#194](https://github.com/Ayorinha/ayorai-opensearch/pull/194) records DEC-007, DEC-008 and DEC-009; [#195](https://github.com/Ayorinha/ayorai-opensearch/pull/195) addresses prediction counts by original Judge state.
- Open work and evidence must be assessed from the exact commit and check run, not inferred from this page.
- PRs still relevant to this status snapshot: #232 (rectified-field policy awaits the maintainer), #241 (RGC statistical proposal and non-delegated decisions), #242 (audit matrix under review), #189 (transformers dependency impact not reviewed), and #247–#249 (README, experimental-module scope and status-source documentation in PR). PR #235 is closed without merge; #245 and #246 are merged.

## Engineering gates

- The deterministic Judge alone owns factual verdicts.
- Frozen evaluation artifacts, manifests, and hashes must not be changed to make tests pass.
- Governance calls for human independent approval of the exact PR SHA and green required checks. The current ruleset enforces the required checks but does not require a reviewer count; automated review comments do not count as human independent approval.
- A CI result is evidence for the commit tested; it is not automatically an independent review.
- Do not claim performance, legal compliance, production readiness, or institutional partnership without appropriate evidence.

For requirement-level status, implementation paths, tests, evidence, and limitations, use the [TRACEABILITY MASTER](TRACEABILITY-MASTER.md).
