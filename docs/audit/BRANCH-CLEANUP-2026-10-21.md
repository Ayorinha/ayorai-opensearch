# Branch cleanup audit — refreshed 2026-10-21

> **Aviso histórico — 2026-10-23:** este documento registra uma versão, auditoria, avaliação ou rascunho anterior; preserve-o como evidência histórica e não o trate como estado atual nem como resultado de benchmark vigente. Consulte docs/STATUS.md.


- Repository: `Ayorinha/ayorai-opensearch`
- Snapshot main SHA: `210af8fdf4fe48b4d092120617b261602eb8ea92`
- Remote branches enumerated: 205 across three pages.
- Closed/merged PR records examined: 350.
- Existing eligible branches identified: 163.
- Branches explicitly deleted by this cleanup operation: **0**.

## Result and limitation

The available GitHub integration exposes branch listing, file/commit creation, ref updates and pull-request operations, but no remote branch-delete operation. No DELETE-ref request or `git push --delete` was executed. This report does not claim that any remote branch was manually removed; GitHub may also automatically delete a PR head branch after merge, which is outside this cleanup action.

The candidate set includes existing remote branches associated with merged PRs and PRs explicitly closed as duplicate/superseded. It excludes `main`, `release/*`, `eval/rgc-pilot`, tag-like refs and branches without a PR association. Branches absent from the remote branch inventory were not listed, even if their PR is merged.

## Branches deleted by this operation

None.

## Eligible existing branches not deleted

| Remote branch | Associated PR(s) | PR status |
|---|---|---|
| `a1-namespace-migration` | [#7](https://github.com/Ayorinha/ayorai-opensearch/pull/7) | mesclada |
| `a2-1-true-coverage-ratchet` | [#9](https://github.com/Ayorinha/ayorai-opensearch/pull/9) | mesclada |
| `a2-2-coverage-map` | [#10](https://github.com/Ayorinha/ayorai-opensearch/pull/10) | mesclada |
| `a2-coverage-ratchet` | [#8](https://github.com/Ayorinha/ayorai-opensearch/pull/8) | mesclada |
| `a3-strict-mypy` | [#11](https://github.com/Ayorinha/ayorai-opensearch/pull/11) | mesclada |
| `a4-golden-baseline-runner` | [#13](https://github.com/Ayorinha/ayorai-opensearch/pull/13) | mesclada |
| `a4-golden-v0-review` | [#12](https://github.com/Ayorinha/ayorai-opensearch/pull/12) | mesclada |
| `chore/authorship` | [#89](https://github.com/Ayorinha/ayorai-opensearch/pull/89) | mesclada |
| `chore/integrity-gates` | [#97](https://github.com/Ayorinha/ayorai-opensearch/pull/97) | mesclada |
| `chore/update-dependency-review-v5` | [#83](https://github.com/Ayorinha/ayorai-opensearch/pull/83) | mesclada |
| `docs-finalize-v0-4-0-release-metadata` | [#151](https://github.com/Ayorinha/ayorai-opensearch/pull/151) | mesclada |
| `docs/addendum-legal-domain-evidence-citations` | [#140](https://github.com/Ayorinha/ayorai-opensearch/pull/140) | mesclada |
| `docs/adr-002-accepted-2026-09-30` | [#25](https://github.com/Ayorinha/ayorai-opensearch/pull/25) | mesclada |
| `docs/adr-009-draft` | [#127](https://github.com/Ayorinha/ayorai-opensearch/pull/127) | mesclada |
| `docs/approve-dec-005-option-a` | [#135](https://github.com/Ayorinha/ayorai-opensearch/pull/135) | mesclada |
| `docs/brand-identity` | [#158](https://github.com/Ayorinha/ayorai-opensearch/pull/158) | mesclada |
| `docs/changelog-integrity` | [#98](https://github.com/Ayorinha/ayorai-opensearch/pull/98) | mesclada |
| `docs/correct-v0-1-manifest-ancestry-note` | [#157](https://github.com/Ayorinha/ayorai-opensearch/pull/157) | mesclada |
| `docs/dec-005-invalid-r1-a-inputs` | [#134](https://github.com/Ayorinha/ayorai-opensearch/pull/134) | mesclada |
| `docs/dec-011-annotation-guide` | [#206](https://github.com/Ayorinha/ayorai-opensearch/pull/206) | mesclada |
| `docs/decision-heading-normalization-2026-10-21` | [#312](https://github.com/Ayorinha/ayorai-opensearch/pull/312) | fechada como duplicada/superada |
| `docs/decision-heading-normalization-2026-10-21-v2` | [#315](https://github.com/Ayorinha/ayorai-opensearch/pull/315) | fechada como duplicada/superada |
| `docs/decisions-pending-v4` | [#130](https://github.com/Ayorinha/ayorai-opensearch/pull/130) | mesclada |
| `docs/doi-v0.5.0` | [#171](https://github.com/Ayorinha/ayorai-opensearch/pull/171) | mesclada |
| `docs/golden-v0-1-manifest` | [#131](https://github.com/Ayorinha/ayorai-opensearch/pull/131) | mesclada |
| `docs/honest-v0-v01-reporting` | [#109](https://github.com/Ayorinha/ayorai-opensearch/pull/109) | mesclada |
| `docs/judge2-boundary-item-2-3` | [#159](https://github.com/Ayorinha/ayorai-opensearch/pull/159) | mesclada |
| `docs/local-evaluation-workflow` | [#43](https://github.com/Ayorinha/ayorai-opensearch/pull/43) | mesclada |
| `docs/m4-status-indexes` | [#137](https://github.com/Ayorinha/ayorai-opensearch/pull/137) | mesclada |
| `docs/m5-adr009-evidence-map` | [#143](https://github.com/Ayorinha/ayorai-opensearch/pull/143) | mesclada |
| `docs/m5-public-claims-audit` | [#138](https://github.com/Ayorinha/ayorai-opensearch/pull/138) | mesclada |
| `docs/manual/chapter-05-operacao-2026-10-21` | [#307](https://github.com/Ayorinha/ayorai-opensearch/pull/307) | fechada como duplicada/superada |
| `docs/manual/chapter-06-seguranca-2026-10-21` | [#308](https://github.com/Ayorinha/ayorai-opensearch/pull/308) | mesclada |
| `docs/manual/chapter-08-avaliacao-2026-10-21` | [#341](https://github.com/Ayorinha/ayorai-opensearch/pull/341) | fechada como duplicada/superada |
| `docs/manual/chapter-08-avaliacao-2026-10-21-rebased` | [#344](https://github.com/Ayorinha/ayorai-opensearch/pull/344) | fechada como duplicada/superada |
| `docs/manual/chapter-08-avaliacao-rebased-2026-10-21` | [#346](https://github.com/Ayorinha/ayorai-opensearch/pull/346) | fechada como duplicada/superada |
| `docs/master-gate-progress-2026-09-30` | [#26](https://github.com/Ayorinha/ayorai-opensearch/pull/26) | mesclada |
| `docs/neutral-authorship-review-attribution` | [#133](https://github.com/Ayorinha/ayorai-opensearch/pull/133) | mesclada |
| `docs/pr-0-1-metric-accuracy-context` | [#116](https://github.com/Ayorinha/ayorai-opensearch/pull/116) | mesclada |
| `docs/pr-0-2-golden-disclosure-glossary` | [#117](https://github.com/Ayorinha/ayorai-opensearch/pull/117) | mesclada |
| `docs/pr-0-3-golden-review-state-note` | [#118](https://github.com/Ayorinha/ayorai-opensearch/pull/118) | mesclada |
| `docs/pr-0-4-adr-index` | [#119](https://github.com/Ayorinha/ayorai-opensearch/pull/119) | mesclada |
| `docs/pr-0-5-traceability-master` | [#120](https://github.com/Ayorinha/ayorai-opensearch/pull/120) | mesclada |
| `docs/progress-final` | [#24](https://github.com/Ayorinha/ayorai-opensearch/pull/24) | mesclada |
| `docs/provenance-model` | [#128](https://github.com/Ayorinha/ayorai-opensearch/pull/128) | mesclada |
| `docs/ptbr-annotation-protocol` | [#145](https://github.com/Ayorinha/ayorai-opensearch/pull/145) | mesclada |
| `docs/ptbr-source-registry` | [#146](https://github.com/Ayorinha/ayorai-opensearch/pull/146) | mesclada |
| `docs/public-metadata-v0-4-0` | [#156](https://github.com/Ayorinha/ayorai-opensearch/pull/156) | mesclada |
| `docs/q2-zero-coverage-scope` | [#141](https://github.com/Ayorinha/ayorai-opensearch/pull/141) | mesclada |
| `docs/r20-r19-status` | [#80](https://github.com/Ayorinha/ayorai-opensearch/pull/80) | mesclada |
| `docs/research-rn-001-second-layer-questioning` | [#152](https://github.com/Ayorinha/ayorai-opensearch/pull/152) | mesclada |
| `docs/rgc-current-preregistration-reading-2026-10-21-rebased` | [#319](https://github.com/Ayorinha/ayorai-opensearch/pull/319) | fechada como duplicada/superada |
| `docs/rgc-current-preregistration-reading-2026-10-21-v2` | [#322](https://github.com/Ayorinha/ayorai-opensearch/pull/322) | fechada como duplicada/superada |
| `docs/rgc-preregistration-reading-note-2026-10-21` | [#310](https://github.com/Ayorinha/ayorai-opensearch/pull/310) | fechada como duplicada/superada |
| `docs/rgc-preregistration-reading-note-2026-10-21-rebased` | [#318](https://github.com/Ayorinha/ayorai-opensearch/pull/318) | fechada como duplicada/superada |
| `docs/rgc-preregistration-reading-note-2026-10-21-v2` | [#313](https://github.com/Ayorinha/ayorai-opensearch/pull/313) | fechada como duplicada/superada |
| `docs/tech-radar-2026-10` | [#115](https://github.com/Ayorinha/ayorai-opensearch/pull/115) | mesclada |
| `docs/threat-model` | [#94](https://github.com/Ayorinha/ayorai-opensearch/pull/94) | mesclada |
| `docs/update-verification-status` | [#47](https://github.com/Ayorinha/ayorai-opensearch/pull/47) | mesclada |
| `eval/dec-017-invalid-prediction-approval-2026-10-21` | [#317](https://github.com/Ayorinha/ayorai-opensearch/pull/317) | fechada como duplicada/superada |
| `eval/dec-017-invalid-prediction-approval-2026-10-21-rebased` | [#321](https://github.com/Ayorinha/ayorai-opensearch/pull/321) | fechada como duplicada/superada |
| `eval/dec-018-hidden-confirmatory-partition-2026-10-21-approved` | [#338](https://github.com/Ayorinha/ayorai-opensearch/pull/338) | fechada como duplicada/superada |
| `eval/dec-018-hidden-confirmatory-partition-2026-10-21-final` | [#340](https://github.com/Ayorinha/ayorai-opensearch/pull/340) | fechada como duplicada/superada |
| `eval/dec-018-hidden-confirmatory-partition-2026-10-21-final2` | [#343](https://github.com/Ayorinha/ayorai-opensearch/pull/343) | fechada como duplicada/superada |
| `eval/dec-018-restore-approved-hidden-scope-2026-10-21` | [#334](https://github.com/Ayorinha/ayorai-opensearch/pull/334) | fechada como duplicada/superada |
| `eval/dec-019-article-cluster-bootstrap-2026-10-21` | [#330](https://github.com/Ayorinha/ayorai-opensearch/pull/330) | fechada como duplicada/superada |
| `eval/dec-019-article-cluster-bootstrap-2026-10-21-final` | [#347](https://github.com/Ayorinha/ayorai-opensearch/pull/347) | fechada como duplicada/superada |
| `eval/dec-019-article-cluster-bootstrap-2026-10-21-rebased` | [#348](https://github.com/Ayorinha/ayorai-opensearch/pull/348) | fechada como duplicada/superada |
| `eval/dec-020-kappa-criteria-2026-10-21-rebased` | [#350](https://github.com/Ayorinha/ayorai-opensearch/pull/350) | fechada como duplicada/superada |
| `eval/f1.2-results` | [#113](https://github.com/Ayorinha/ayorai-opensearch/pull/113) | mesclada |
| `eval/golden-v1-provenance-edge` | [#46](https://github.com/Ayorinha/ayorai-opensearch/pull/46) | mesclada |
| `eval/preregister-f1.2` | [#112](https://github.com/Ayorinha/ayorai-opensearch/pull/112) | mesclada |
| `eval/pt-cp-audit-sim` | [#114](https://github.com/Ayorinha/ayorai-opensearch/pull/114) | mesclada |
| `f1-5-v0-4-0-documentation-dec007` | [#148](https://github.com/Ayorinha/ayorai-opensearch/pull/148) | mesclada |
| `feat/0-9-semantic-digest-v1` | [#122](https://github.com/Ayorinha/ayorai-opensearch/pull/122) | mesclada |
| `feat/1-2a-api-contract` | [#125](https://github.com/Ayorinha/ayorai-opensearch/pull/125) | mesclada |
| `feat/1-2b-sqlite-migration` | [#126](https://github.com/Ayorinha/ayorai-opensearch/pull/126) | mesclada |
| `feat/1-3-remove-legacy-verification-status` | [#129](https://github.com/Ayorinha/ayorai-opensearch/pull/129) | mesclada |
| `feat/api-contract-guard-stage-b` | [#162](https://github.com/Ayorinha/ayorai-opensearch/pull/162) | mesclada |
| `feat/api-response-contract-item-2-5` | [#163](https://github.com/Ayorinha/ayorai-opensearch/pull/163) | mesclada |
| `feat/close-evaluation-layer` | [#48](https://github.com/Ayorinha/ayorai-opensearch/pull/48) | mesclada |
| `feat/f1-3-response-policy` | [#132](https://github.com/Ayorinha/ayorai-opensearch/pull/132) | mesclada |
| `feat/f1-3-response-policy-implementation` | [#136](https://github.com/Ayorinha/ayorai-opensearch/pull/136) | mesclada |
| `feat/f1-multilingual-stance` | [#91](https://github.com/Ayorinha/ayorai-opensearch/pull/91) | mesclada |
| `feat/golden-pt-source-corpus` | [#103](https://github.com/Ayorinha/ayorai-opensearch/pull/103) | mesclada |
| `feat/golden-r2-migration-item-2-6` | [#165](https://github.com/Ayorinha/ayorai-opensearch/pull/165) | mesclada |
| `feat/integrated-verification-pipeline` | [#65](https://github.com/Ayorinha/ayorai-opensearch/pull/65) | mesclada |
| `feat/judge2-canonical-output-item-2-4` | [#160](https://github.com/Ayorinha/ayorai-opensearch/pull/160) | mesclada |
| `feat/judge2-explanations-traceability-item-2-7` | [#167](https://github.com/Ayorinha/ayorai-opensearch/pull/167) | mesclada |
| `feat/judge2-r2-a-api-item-2-5` | [#161](https://github.com/Ayorinha/ayorai-opensearch/pull/161) | mesclada |
| `feat/judge2-rfc8785-canonicalization` | [#164](https://github.com/Ayorinha/ayorai-opensearch/pull/164) | mesclada |
| `feat/opentelemetry-trace-sink-adapter` | [#81](https://github.com/Ayorinha/ayorai-opensearch/pull/81) | mesclada |
| `feat/r10-arena-report` | [#59](https://github.com/Ayorinha/ayorai-opensearch/pull/59) | mesclada |
| `feat/r11-bounded-optimizer` | [#71](https://github.com/Ayorinha/ayorai-opensearch/pull/71) | mesclada |
| `feat/r11-gepa-optimization-core` | [#60](https://github.com/Ayorinha/ayorai-opensearch/pull/60) | mesclada |
| `feat/r12-mcp-tool-registry` | [#61](https://github.com/Ayorinha/ayorai-opensearch/pull/61) | mesclada |
| `feat/r13-tenant-context` | [#70](https://github.com/Ayorinha/ayorai-opensearch/pull/70) | mesclada |
| `feat/r13-tenant-isolation` | [#62](https://github.com/Ayorinha/ayorai-opensearch/pull/62) | mesclada |
| `feat/r14-trace-context` | [#72](https://github.com/Ayorinha/ayorai-opensearch/pull/72) | mesclada |
| `feat/r15-job-executor` | [#73](https://github.com/Ayorinha/ayorai-opensearch/pull/73) | mesclada |
| `feat/r17-trace-export-boundary` | [#75](https://github.com/Ayorinha/ayorai-opensearch/pull/75) | mesclada |
| `feat/r18-tenant-runtime-propagation` | [#76](https://github.com/Ayorinha/ayorai-opensearch/pull/76) | mesclada |
| `feat/r19-arena-report-serialization` | [#77](https://github.com/Ayorinha/ayorai-opensearch/pull/77) | mesclada |
| `feat/r1a-verify-api` | [#39](https://github.com/Ayorinha/ayorai-opensearch/pull/39) | mesclada |
| `feat/r1b-golden-judge-bridge` | [#40](https://github.com/Ayorinha/ayorai-opensearch/pull/40) | mesclada |
| `feat/r2-audit-api` | [#38](https://github.com/Ayorinha/ayorai-opensearch/pull/38) | mesclada |
| `feat/r2-audit-persistence` | [#49](https://github.com/Ayorinha/ayorai-opensearch/pull/49) | mesclada |
| `feat/r20-evaluation-content-digest` | [#78](https://github.com/Ayorinha/ayorai-opensearch/pull/78) | mesclada |
| `feat/r3-council-orchestration` | [#50](https://github.com/Ayorinha/ayorai-opensearch/pull/50) | mesclada |
| `feat/r4-replay-store` | [#52](https://github.com/Ayorinha/ayorai-opensearch/pull/52) | mesclada |
| `feat/r5-opensearch-hybrid-pipeline` | [#53](https://github.com/Ayorinha/ayorai-opensearch/pull/53) | mesclada |
| `feat/r6-grounded-synthesis-v2` | [#55](https://github.com/Ayorinha/ayorai-opensearch/pull/55) | mesclada |
| `feat/r7-adversarial-redteam-main` | [#64](https://github.com/Ayorinha/ayorai-opensearch/pull/64) | mesclada |
| `feat/r8-metrics-prometheus-export` | [#67](https://github.com/Ayorinha/ayorai-opensearch/pull/67) | mesclada |
| `feat/r8-observability-metrics` | [#57](https://github.com/Ayorinha/ayorai-opensearch/pull/57) | mesclada |
| `feat/r9-durable-job-store-main` | [#63](https://github.com/Ayorinha/ayorai-opensearch/pull/63) | mesclada |
| `feat/r9-job-leases` | [#66](https://github.com/Ayorinha/ayorai-opensearch/pull/66) | mesclada |
| `fix/0-6-isolate-attractor-runtime-data` | [#121](https://github.com/Ayorinha/ayorai-opensearch/pull/121) | mesclada |
| `fix/ci-concurrency-per-ref` | [#108](https://github.com/Ayorinha/ayorai-opensearch/pull/108) | mesclada |
| `fix/dec005-r1a-invalid-input-422` | [#139](https://github.com/Ayorinha/ayorai-opensearch/pull/139) | mesclada |
| `fix/f0-recovery` | [#88](https://github.com/Ayorinha/ayorai-opensearch/pull/88) | mesclada |
| `fix/gap-b-excerpt-revalidation` | [#99](https://github.com/Ayorinha/ayorai-opensearch/pull/99) | mesclada |
| `fix/golden-abstention-metric-contract` | [#82](https://github.com/Ayorinha/ayorai-opensearch/pull/82) | mesclada |
| `fix/golden-runner-r20-newline` | [#79](https://github.com/Ayorinha/ayorai-opensearch/pull/79) | mesclada |
| `fix/golden-runner-remove-canary` | [#68](https://github.com/Ayorinha/ayorai-opensearch/pull/68) | mesclada |
| `fix/governance-restore-dec017-pending-2026-10-21` | [#329](https://github.com/Ayorinha/ayorai-opensearch/pull/329) | fechada como duplicada/superada |
| `fix/opensearch-max-agents-legacy-coercion` | [#169](https://github.com/Ayorinha/ayorai-opensearch/pull/169) | mesclada |
| `fix/path-b-license-provenance` | [#110](https://github.com/Ayorinha/ayorai-opensearch/pull/110) | mesclada |
| `fix/pin-actions-sha` | [#96](https://github.com/Ayorinha/ayorai-opensearch/pull/96) | mesclada |
| `fix/pt-stance-negation-date-antonym` | [#111](https://github.com/Ayorinha/ayorai-opensearch/pull/111) | mesclada |
| `fix/r1-green-ci` | [#36](https://github.com/Ayorinha/ayorai-opensearch/pull/36) | mesclada |
| `fix/replay-digest-integrity` | [#95](https://github.com/Ayorinha/ayorai-opensearch/pull/95) | mesclada |
| `fix/ruff-up017-2026-10-01` | [#28](https://github.com/Ayorinha/ayorai-opensearch/pull/28) | mesclada |
| `github-community-track` | [#21](https://github.com/Ayorinha/ayorai-opensearch/pull/21) | mesclada |
| `hardening/supply-chain-r16` | [#74](https://github.com/Ayorinha/ayorai-opensearch/pull/74) | mesclada |
| `launch-post-draft` | [#23](https://github.com/Ayorinha/ayorai-opensearch/pull/23) | mesclada |
| `phase-1-1-frozen-legacy-baseline` | [#123](https://github.com/Ayorinha/ayorai-opensearch/pull/123) | mesclada |
| `phase-1-1b-pin-ubuntu-24-04` | [#124](https://github.com/Ayorinha/ayorai-opensearch/pull/124) | mesclada |
| `phase0-final-record` | [#14](https://github.com/Ayorinha/ayorai-opensearch/pull/14) | mesclada |
| `portfolio-attractor-readme` | [#22](https://github.com/Ayorinha/ayorai-opensearch/pull/22) | mesclada |
| `q1-verification-backends-coverage-85` | [#147](https://github.com/Ayorinha/ayorai-opensearch/pull/147) | mesclada |
| `q3-q5-resource-lifecycle-cli-pr` | [#149](https://github.com/Ayorinha/ayorai-opensearch/pull/149) | mesclada |
| `r1-a-strict-verification-models-2026-09-30-v2` | [#27](https://github.com/Ayorinha/ayorai-opensearch/pull/27) | mesclada |
| `r1-verification-complete-2026-10-01` | [#31](https://github.com/Ayorinha/ayorai-opensearch/pull/31) | mesclada |
| `r2-audit-mode-2026-10-01` | [#32](https://github.com/Ayorinha/ayorai-opensearch/pull/32) | mesclada |
| `r3-r4-core-2026-10-01` | [#33](https://github.com/Ayorinha/ayorai-opensearch/pull/33) | mesclada |
| `r5-r6-r8-r10-core-2026-10-01` | [#34](https://github.com/Ayorinha/ayorai-opensearch/pull/34) | mesclada |
| `r9-durable-core-2026-10-01` | [#35](https://github.com/Ayorinha/ayorai-opensearch/pull/35) | mesclada |
| `security/sbom-artifact` | [#84](https://github.com/Ayorinha/ayorai-opensearch/pull/84) | mesclada |
| `test/f1-4-authority-cli-contract` | [#144](https://github.com/Ayorinha/ayorai-opensearch/pull/144) | mesclada |
| `test/failure-engine-edge-cases` | [#44](https://github.com/Ayorinha/ayorai-opensearch/pull/44) | mesclada |
| `test/null-body-fastapi-pydantic-compat-2026-10-21` | [#325](https://github.com/Ayorinha/ayorai-opensearch/pull/325) | fechada como duplicada/superada |
| `test/null-body-fastapi-pydantic-compat-2026-10-21-final` | [#327](https://github.com/Ayorinha/ayorai-opensearch/pull/327) | fechada como duplicada/superada |
| `test/null-body-fastapi-pydantic-compat-2026-10-21-final2` | [#332](https://github.com/Ayorinha/ayorai-opensearch/pull/332) | fechada como duplicada/superada |
| `test/null-body-fastapi-pydantic-compat-2026-10-21-rebase-2` | [#336](https://github.com/Ayorinha/ayorai-opensearch/pull/336) | fechada como duplicada/superada |
| `test/null-body-fastapi-pydantic-compat-2026-10-21-rebased` | [#328](https://github.com/Ayorinha/ayorai-opensearch/pull/328) | fechada como duplicada/superada |
| `test/openai-compatible-error-contracts-2026-10-21` | [#324](https://github.com/Ayorinha/ayorai-opensearch/pull/324) | fechada como duplicada/superada |
| `test/opensearch-provider-coverage` | [#45](https://github.com/Ayorinha/ayorai-opensearch/pull/45) | mesclada |
| `test/property-evidence-graph` | [#41](https://github.com/Ayorinha/ayorai-opensearch/pull/41) | mesclada |
| `test/provider-contracts` | [#42](https://github.com/Ayorinha/ayorai-opensearch/pull/42) | mesclada |
| `wave2-judge2-item-2-1` | [#150](https://github.com/Ayorinha/ayorai-opensearch/pull/150) | mesclada |
| `wave2-judge2-item-2-2-gates` | [#153](https://github.com/Ayorinha/ayorai-opensearch/pull/153) | mesclada |
| `wave2-judge2-item-2-3-decision-rules` | [#154](https://github.com/Ayorinha/ayorai-opensearch/pull/154) | mesclada |

## Protected and excluded branches

- `main`
- Any `release/*` branch
- `eval/rgc-pilot`
- Tag refs
- Branches without a PR association

## Follow-up

When a branch-delete operation is available, delete only the listed candidates after confirming no active workflow depends on them. Keep all excluded branches intact. This inventory is not proof that cleanup was executed.
