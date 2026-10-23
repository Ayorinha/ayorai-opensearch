# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-23

This file is the single source of current project status. Historical documents describe the SHA they audited and must not be treated as a live status dashboard.

Historical snapshots and the previous execution-cycle merge table are preserved in [docs/history/STATUS-SNAPSHOTS.md](history/STATUS-SNAPSHOTS.md).

## Consolidated process and RGC runner update — 2026-10-23

- **Reference `main` SHA for this batch:** `641591973da25ede8234958b0a36b62423476630`.
- **Origin of commit `6415919`: merged via PR #398, not a direct push.** PR: [#398 — strict validation of gold-label JSONL](https://github.com/Ayorinha/ayorai-opensearch/pull/398). Reviewed head SHA: `d2cf29aa4fbb9b519955b22e3b036a9a18f3c9b6`; merge commit: `641591973da25ede8234958b0a36b62423476630`. This was not a process deviation.
- **PR #398 head checks (all completed successfully on that exact head SHA):** [CI](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814878), [CodeQL](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814819), [Security](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814840), [Dependency Review](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814854), [API Contract Guard](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814873), [Schemathesis Full API Contract](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814957), [Golden r2 Migration](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814783), and [RGC Design Simulation](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39761814921). These results apply to the PR #398 head SHA, not to a different commit.
- **Runner version:** the strict gold-label JSONL contract is a material input-contract change; `RUNNER_VERSION` and the synthetic report assertion are advanced to `rgc-eval/0.7.0`. Labels that relied on type coercion or blank-line tolerance may now be rejected.
- **Extraction history (2026-10-22):** evidence end offset uses `start_offset + len(content)` when absent; NLI payloads are validated strictly; missing confidence defaults to `0.0` (“sem nota”), not a verdict. See [PR #391](https://github.com/Ayorinha/ayorai-opensearch/pull/391) and [PR #393](https://github.com/Ayorinha/ayorai-opensearch/pull/393).
- **Current batch:** [PR #399](https://github.com/Ayorinha/ayorai-opensearch/pull/399) consolidates strict source-document validation, runner-version alignment, the runner specification, changelog, and this single STATUS update. Its head checks must be evaluated separately; PR #398 checks do not validate PR #399.
- **Scientific boundary:** no real RGC case has been evaluated and no benchmark metric has been produced. The protocol remains `[PROPOSTO]`, not frozen. Pilot 02, a second independent human annotation and independent human review F-01 remain pending. No Judge, Golden v0/v0.1, frozen thresholds, preregistration, benchmark cases or release metadata are changed by this batch. No tag or release is authorized.


## Execution snapshot recorded on 2026-10-22

- **Main reference SHA when this snapshot was prepared:** `a44d0564d429d956898e819721299f715b46bda2` — [PR #393 merge commit](https://github.com/Ayorinha/ayorai-opensearch/commit/a44d0564d429d956898e819721299f715b46bda2).
- **PR #391 merged:** [test(extraction): cover provenance and adapter contracts](https://github.com/Ayorinha/ayorai-opensearch/pull/391), squash SHA `bf49dba9e7e66bdc0af0203845547b8541e81cca`. The seven PR workflows passed for its reviewed head SHA.
- **PR #393 merged:** [fix(extraction): validate NLI payloads and source offsets](https://github.com/Ayorinha/ayorai-opensearch/pull/393), squash SHA `a44d0564d429d956898e819721299f715b46bda2`. The seven PR workflows passed for reviewed head `e5b0be75295ff32fc5635e2ae8ccde4521980b9f`; these are PR-head results, not a claim that post-merge checks for the resulting main SHA were independently queried.
- **Extraction hardening:** missing evidence end offsets now use `start_offset + len(content)`; NLI adapter payloads are validated strictly and malformed payloads are covered by regression tests. An omitted NLI confidence remains `0.0` as an unscored default, not as a Judge verdict.
- **PR #394 merged:** [docs(status): record extraction fixes and current PR state](https://github.com/Ayorinha/ayorai-opensearch/pull/394), squash SHA `f94e86db89eb000c4764c49b949a30d65e63e421`. This documentation follow-up clarifies that the snapshot above records the state at preparation time, not the current HEAD after this follow-up merge.
- **PR #395 merged:** [docs(status): clarify snapshot timestamp and follow-up merge](https://github.com/Ayorinha/ayorai-opensearch/pull/395), squash SHA `bd99f4b3e25a785cdcc08172d860a317532e6d90`. The current `main` reference after this documentation-only merge is `bd99f4b3e25a785cdcc08172d860a317532e6d90`; the historical CI statements above refer to their explicitly named commit/PR heads, not to post-merge checks for this SHA. The combined-status query returned no status records, so main CI is not confirmed by that query.
- **PR #396 merged:** [docs(status): record PR #395 merge and main reference](https://github.com/Ayorinha/ayorai-opensearch/pull/396), squash SHA `f7277d3e00a0efb8c47d8a5366bc9eba0db38778`. All seven PR workflows passed for reviewed head `da3ad5f9cc0145154e38cb1f62fbee137cd8fdfd`, including CI on Python 3.11, 3.12 and 3.13, Security, CodeQL, Dependency Review, API Contract Guard, Schemathesis and Golden r2 Migration. These are PR-head results; they are not a claim that post-merge main checks were separately queried.
- **Release state:** v0.5.0 remains the latest published release; v0.6.0 remains a draft. No tag or release was created by this work.
- **Scientific boundary unchanged:** RGC PT-BR remains `[PROPOSTO]`, not frozen. Pilot 02, a second independent human annotation and independent human review F-01 remain pending. No RGC cases were created/labeled by AI, no ATTRACTOR execution over pilot/benchmark cases occurred, and no RGC metrics or external-validation claims were produced.
- **Scope boundary:** Judge, Golden manifests/hashes, preregistration, benchmark cases and release metadata were not changed by PRs #391 or #393.

The execution snapshot above is historical as of its preparation time. Historical snapshots below remain historical and are not retroactively rewritten.

## API contract note (2026-10-21) — r1-a JSON null

The frozen contract remains HTTP 422 with error type `missing` and location `["body"]`; the fixture `tests/fixtures/r1-a-error-baseline.json` was not modified. The controlled isolated reproduction in [`scripts/repro_null_body_contract.py`](../scripts/repro_null_body_contract.py) tested 16 FastAPI/Pydantic combinations: FastAPI `0.115.0, 0.117.0, 0.119.0, 0.121.0, 0.123.0, 0.125.0, 0.127.0, 0.128.2`, each paired with Pydantic `2.10.0` and `2.13.5`, plus `httpx==0.27.2`. Both synthetic route styles reflecting the v0.4.0 typed-body route and v0.5.0 Any/Body + manual validation route returned 422 `missing`; direct `model_validate(None, from_attributes=True)` returned `model_attributes_type` in both tested Pydantic versions. No version threshold was identified; no dependency bound was added. Exact commands are recorded in CHANGELOG.md and the workflow from PR #339. This reproduces the relevant route styles in isolation rather than importing the tagged application, and does not establish behavior outside the tested matrix.

**Correction dated 2026-10-21:** the paragraph above describes only the initial 16-combination matrix and is historical. The expanded controlled bisection found the first change in the typed-route style between FastAPI `0.150.0` (`missing`) and `0.151.0` (`model_attributes_type`); the v0.5.0 explicit `payload is None` guard preserves HTTP 422 `missing` through FastAPI `0.157.0` with Pydantic tested through `2.14.1`. No API, fixture or dependency bound changed; see the final bisection result in `CHANGELOG.md`.

## Current execution snapshot (2026-10-21)

- **SHA de referência validado antes desta atualização documental:** `c9994dd2ef907f05b603626f4845b44739c285ca`. Esta é a revisão da `main` que incorpora o fechamento das etapas 1–3; esta PR atualiza somente status e rascunho de release, portanto seu próprio merge terá outro SHA.
- **CI da referência:** [run 39638074704](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39638074704) concluído: **12 checks com sucesso, 1 ignorado** por condição de workflow (`rgc-design-simulation`), zero falhas. Testes Python 3.11, 3.12 e 3.13 passaram.
- **Segurança e análise estática:** [security run 39638075257](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39638075257) e [CodeQL/analyze run 39638074782](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39638074782) concluídos com sucesso.
- **Saída de testes (Python 3.12):** `1126 passed, 1 skipped in 47.79s`; cobertura geral 94% (4.214 statements, 251 missed). O job `namespace-compatibility` também executou `pytest -q` e passou.
- **Qualidade no CI:** `ruff check .` — `All checks passed!`; `ruff format --check .` — `360 files already formatted`; `mypy --strict evals/ptbr/rgc_eval.py evals/ptbr/rgc_agreement.py` — `Success: no issues found in 3 source files`. O mypy estrito geral também passou: 91 source files sem erros.
- **PRs mescladas neste fechamento:** #362 (guarda inicial de consistência; SHA `0f06995f51d3d2cfded56b849c7300ac7c3b3300`); #369 (guarda de emendas; SHA `1e77df724d432b05d230b112afd3ca6ff83eb3b0`); #370 (consistência documental; SHA `7fc9ae9708ff8ee46ffe2398efa4d6024d36ce90`); #373 (justificativas `# nosec`; SHA `fc12c38e5bc2967642d2bd941d01fc52b4f206fb`); #374 (status/rascunho anterior; SHA `a269d5f5371f3b2545635515d6b98d8cfe679ba6`); #375 (consolidação da guarda, removeu o teste duplicado; SHA `daf9ce3771712f60ddce2ff76e7118d25fafb656`); #376 (auditoria de desvios de processo; SHA `c9994dd2ef907f05b603626f4845b44739c285ca`).
- **PRs fechadas sem merge:** #371 foi substituída por esta atualização final; #372 foi substituída pela #373; #367 foi substituída pela #373; #368 foi substituída pela #370. A #373, não a #372, é o merge efetivo das justificativas `# nosec`.
- **Fechamentos anteriores do mesmo ciclo:** #307, #328, #330, #334, #336, #338, #340, #343, #344, #346, #348 e #350 permanecem registrados no snapshot histórico e no relatório de limpeza de branches.
- **PRs abertas no snapshot de referência:** nenhuma. A PR atual de status/release é criada depois desse snapshot; após seu merge, a API será consultada novamente para confirmar zero PRs abertas.
- **Branches remotas:** nenhuma branch foi apagada. A auditoria de candidatas permanece em [BRANCH-CLEANUP-2026-10-21.md](audit/BRANCH-CLEANUP-2026-10-21.md); a limpeza das aproximadamente 205 branches requer ação manual autorizada.
- **Limites científicos:** DEC-017–DEC-020 continuam aprovadas. O protocolo RGC permanece `[PROPOSTO]`, não congelado. Nenhum caso de piloto/benchmark foi criado, completado ou rotulado; o ATTRACTOR não foi executado em casos RGC e nenhuma métrica RGC foi produzida. A revisão automatizada não é independente; F-01 continua aberto.

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


## Incremental benchmark-integrity update — 2026-10-21

**Reference SHA before this status-only update:** `eade15e0e1475689f329d8d382c12eada2f894e1`. This snapshot records the merged engineering work below; the final SHA of this documentation update must be read from its merge commit, not predicted here.

- **PR #378** — `feat(eval): enforce RGC protocol freeze gate`: RGC evaluation fails closed unless the protocol, preregistration, runner specification and an explicit freeze manifest are present.
- **PR #379** — `fix(eval): bind RGC freeze to runner integrity`: the freeze manifest binds the exact protocol, preregistration, runner specification, runner code and runner version.
- **PR #380** — `fix(eval): require declared source provenance in pilot checker`: each filled pilot case must identify a captured source, and the excerpt must be found literally in that declared source. Synthetic regression tests cover missing, unknown and mismatched source identifiers. PR #380 CI completed with 19 successful checks and one conditionally skipped design-simulation job; no checks failed.

**Scientific status is unchanged:** the RGC PT-BR protocol remains `[PROPOSTO]`; no real pilot or benchmark cases were created or labeled by this engineering work, the ATTRACTOR was not run on RGC cases, and no RGC metrics were produced. No real freeze manifest, tag or release was created. The automated checks are not an independent human review, and F-01 remains open.

**Next blocking dependency:** a human must conduct pilot 02 privately, without AI assistance and without running the ATTRACTOR, then record only methodological findings. A second annotator and independent human review remain necessary before a maintainer freeze decision and any definitive dataset work.

## Incremental benchmark-integrity update — 2026-10-21 (runner 0.6.0)

**Reference SHA before this status update:** `970af6ddc7d912552e18fbc01bed534242f9b56a`. This status-only PR records the subsequent integrity work; read the merge commit for the resulting `main` SHA.

- **PR #381** — `docs(status): record RGC freeze and provenance gates`, SHA `9045549a81f4ad024782598698e2061a3a7d13c0`.
- **PR #382** — `feat(eval): require RGC annotation approval evidence`, SHA `44291a2ad2b89e783f725394c9297d982c25536a`. Evaluation now requires human agreement/adjudication evidence bound to the exact annotation inputs, cases, labels, development partition and report; agreement reports preserve input hashes.
- **PR #383** — `ci: run RGC design simulation on relevant changes`, SHA `ea4e7de19bfe9132501e466075334dddaede61d5`. The synthetic design simulation has a dedicated workflow, manual dispatch and artifact preservation.
- **PR #384** — `test(rgc): cover synthetic design simulation invariants`, SHA `5ad402ab9f73e6b592d5fb75168d54030ae2a196`. Added deterministic tests for agreement coefficients, baseline tie-breaking and synthetic prediction accuracy. All checks, including the RGC design simulation, passed for this PR.
- **PR #385** — `fix(eval): advance RGC runner version to 0.6.0`, SHA `970af6ddc7d912552e18fbc01bed534242f9b56a`. The executor version now matches the material changes to protocol-freeze, runner-integrity, source-provenance and annotation-approval gates. PR CI and post-merge CI, security and CodeQL all passed; the dedicated synthetic design-simulation workflow also completed successfully ([run 39649859657](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/39649859657)).

**Scientific status is unchanged:** the RGC PT-BR protocol remains `[PROPOSTO]`, not frozen. No real pilot or definitive benchmark cases were created, reviewed or labeled by this engineering work. The ATTRACTOR was not run on RGC cases and no RGC metrics were produced. No real freeze manifest, tag or release was created. F-01 remains open and automated review is not independent human review.

**Blocking human work:** conduct pilot 02 privately without AI assistance or ATTRACTOR execution; obtain a second independent annotation; complete human review F-01; then make separate maintainer decisions about protocol freeze and the hidden partition's provenance/isolation gates.


## Additional benchmark-integrity limitation — independent annotator identity

The RGC runner binds annotation A and B by SHA-256, verifies the agreement report and requires a passing Cohen's kappa gate plus an approval/adjudication record. These controls establish artifact integrity, not the real-world identity of the people who produced the two files. The current manifest schema does not independently prove that annotator A and annotator B are different people.

- **Operational gate:** the human approver must explicitly attest that the annotations were produced independently by two different people and preserve the attestation with the private study records.
- **Possible technical hardening:** add distinct pseudonymous annotator identifiers to the agreement report and approval manifest, validate that the identifiers differ, and test missing/equal identifiers fail closed.
- **Decision boundary:** this would change the benchmark artifact schema and must be explicitly approved by the maintainer before implementation. No such schema change is made here.

This limitation does not authorize pilot case creation, system execution, protocol freeze, or benchmark claims.


## Current execution update — 2026-10-21 (manual index reconciliation)

- **Current reference SHA:** `620e39f7e2fb7437b576d7dc935cab6ffcbe08b0` ([PR #388 merge](https://github.com/Ayorinha/ayorai-opensearch/commit/620e39f7e2fb7437b576d7dc935cab6ffcbe08b0)).
- **PR #388:** merged by squash after all seven associated workflow runs completed successfully: CI, Security, CodeQL, Dependency Review, API Contract Guard, Schemathesis Full API Contract, and Golden r2 Migration. The latest run results showed success for all seven workflows.
- **Manual index:** `docs/manual/README.md` now links all ten existing chapters and explains that `Atual` is a documentation status, not proof of automatic revalidation against HEAD.
- **Open PRs:** none were returned by the repository open-PR search immediately after the merge.
- **Scientific and release boundaries unchanged:** RGC remains `[PROPOSTO]`, not frozen; no real pilot/benchmark cases or RGC metrics were created by this engineering work; F-01 and the independent human annotation/review gates remain open. v0.6.0 remains a draft and no release/tag is authorized by this update.
