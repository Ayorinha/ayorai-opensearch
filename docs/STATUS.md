# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-21

This file is the single source of current project status. Historical documents describe the SHA they audited and must not be treated as a live status dashboard.

Historical snapshots and the previous execution-cycle merge table are preserved in [docs/history/STATUS-SNAPSHOTS.md](history/STATUS-SNAPSHOTS.md).

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
