# Auditoria pós-encerramento — 2026-11-21

Revisão por ferramenta automatizada, publicada pelo mantenedor.

- **Referência:** `main` @ `2b98ac415e3d56ec851a32f75b9f067424b6f4ee` (#603). CI, Security e CodeQL passaram nesse SHA.
- **Escopo:**
  - revisão pós-merge das PRs #599 a #603;
  - reconciliação de PRs, branches e decisões;
  - estado do RGC.

  Somente leitura na auditoria. As correções vieram em PRs próprias (#604, #605, #606, #609, #610 e #611), mescladas por autorização individual do mantenedor.
- **Não feito:** merge, aprovação, tag, release, exclusão de branch e edição de artefato protegido. Nenhum caso RGC foi aberto, criado, rotulado ou executado. A branch `eval/rgc-pilot` foi só comparada automaticamente com a `main`; seu conteúdo não foi exibido.

## 1. Repositório

- 591 PRs: 452 mescladas, 139 fechadas sem merge, 0 abertas antes desta auditoria. 0 issues abertas.
- 92 branches: `main`, `gh-pages` e 90 outras. O repositório tem `delete_branch_on_merge: true`, então as branches de PRs mescladas são apagadas sozinhas. A contagem de 94, registrada antes no `STATUS.md`, incluía branches de PRs que estavam abertas naquele momento. A origem de uma contagem de 82 citada antes não pôde ser reproduzida.
- Alertas e atualizações de segurança do Dependabot estão desligados: a API responde "Dependabot alerts are disabled for this repository".

## 2. Revisão pós-merge das PRs #599 a #603

As PRs foram mescladas por autorização do mantenedor, com CI verde no HEAD final, mas a revisão técnica não ficou registrada antes do merge. Esta seção faz esse registro depois do fato. Ela não é aprovação.

| PR | Verificação | Resultado |
|---|---|---|
| #599, detector v13 | Toda palavra de escala tem fator; entradas como "1 bi", "mil" sozinho, "R$ 2 mil milhões" e "10 mil mil" não lançam exceção; Golden v0 7/30 e v0.1 11/30 (`1fd6fdb7…`) reproduzidos com `scripts/reproduce.py` | Sem defeito |
| #600, DEC-022 | A revisão publicada na PR deixou dois comentários não bloqueantes: definição de K e texto integral da Emenda 12 no protocolo | Tratados na #605 |
| #601, ADR-011 | O teste de guarda confere o Judge usado por rota; o texto do ADR-009 não remete à ADR-011 | Remissão incluída no índice de ADRs |
| #602, cadeia da trilha | Uma falha na gravação da entrada da cadeia deixava a transação aberta, e a próxima gravação confirmava o rastro que o chamador recebeu como falho; o mesmo valia para o registro de purga | **Defeito** reproduzido por teste e corrigido na #604 |
| #603, governança | O `STATUS.md` dizia "94 branches" e "nenhuma PR aberta"; o índice de ADRs não tinha a ADR-010 | Corrigido nesta PR |

## 3. Decisões

| ID | Estado | Implementação |
|---|---|---|
| DEC-011, 014, 017 a 021, 023, 024, 027 | Aprovadas | Presentes em `evals/ptbr/` e `scripts/benchmarks/phase1b/`, com testes |
| DEC-022 | Aprovada | Implementada (#600). O texto normativo (Emenda 12) depende do mantenedor; a proposta está em `docs/eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md` |
| DEC-025 e DEC-026 | **Só propostas**, em PRs fechadas sem merge (#504 e #509) | Nenhuma. IDs reservados no índice para evitar outra colisão como a de DEC-007 e DEC-008 |

## 4. RGC

- Protocolo **[PROPOSTO]**, não congelado. A Emenda 11 está no pré-registro, mas não no protocolo; a Emenda 12 não está em nenhum dos dois. O texto pronto está na proposta citada acima.
- O guia `docs/annotation/PROTOCOLO.md` (versão de trabalho de 2026-10-11) não repetia os rótulos do RGC. Ganhou uma remissão às Emendas 2, 3, 4 e 10. Um parágrafo genérico do guia sobre `UNVERIFIED` pode ser lido como divergente da Emenda 4 ("ausência de evidência implica `UNVERIFIED`"); fica registrado para decisão do mantenedor.
- Texto superado por retificação: o runner o exclui da adjudicação desde a #609 (`rgc-eval/0.14.0`, campo `superseded_spans` do corpus). O `xfail` foi resolvido. Marcar as fontes retificadas é curadoria humana.
- Não há no repositório evidência de piloto 02, segunda anotação, revisão F-01 ou adjudicação. Esses artefatos devem ficar fora do repositório, então a ausência não prova que não foram feitos.

## 5. Relatórios com caminhos internos

`reports/f1.2-baseline.json`, `reports/f1.2-candidate.json` e `reports/f1.2-results.json` trazem `package_file` com caminhos absolutos de ambientes de execução (`/tmp/…/scratchpad/…`, `/home/…`). A correção existe na branch `chore/sanitize-benchmark-report-paths` (#498, fechada), mas muda o `report_sha256` desses relatórios e depende de decisão do mantenedor.

## 5a. Situação final das pendências (2026-11-21)

| Pendência | Situação |
|---|---|
| Defeito transacional da cadeia (#602) | Resolvido: #604 e #611 |
| Comentários da revisão da #600 | Resolvidos: #605 |
| STATUS, índices de ADR e de decisões | Resolvidos: #606 |
| Texto superado como evidência (`xfail`) | Resolvido: #609 |
| Caminhos internos nos relatórios F1.2; guia × Emenda 4 | Resolvidos: #610 |
| Emendas 11 e 12 nos arquivos protegidos | **Do mantenedor:** inserir o texto de `docs/eval/AMENDMENT-PROPOSAL-2026-11-21-DEC-022.md` |
| Dependabot alerts e security updates | **Do mantenedor:** Settings → Code security |
| Gates humanos do RGC (piloto 02, 2ª anotação, F-01, congelamento) | **De pessoas** |
| Revisão humana independente das PRs deste ciclo | **De pessoas** |
| Exclusão das 22 branches vazias ou incorporadas e triagem das 56 em conflito | **Do mantenedor** (tabela abaixo) |

## 6. Inventário das branches

Método:
- para cada branch, o patch desde a base comum com a `main` foi testado contra a `main` atual;
- **Vazia:** sem commits próprios;
- **Incorporada:** o patch inteiro já está na `main` (aplica ao contrário);
- **Conteúdo não incorporado:** o patch ainda aplicaria limpo;
- **Em conflito:** parcial ou superada por trabalho posterior.

Só as vazias e as incorporadas (22) são candidatas à exclusão com evidência. As em conflito pedem triagem humana. As do Dependabot propõem versões novas dos pins históricos, que ficam fixos por decisão (`docs/security/HISTORICAL-PINS.md`). `eval/rgc-pilot` não deve ser aberta por agentes.

| Classe | Branch | PR (estado) | Último commit | Head | Commits à frente |
|---|---|---|---|---|---|
| Vazia | `docs/audit/branch-cleanup-2026-10-21` | - | 2026-10-21 | `5c205f8f` | 0 |
| Vazia | `docs/deployment-readiness-gates` | - | 2026-10-26 | `e7bce5c5` | 0 |
| Vazia | `docs/manual/chapter-06-security-final-2026-10-21` | - | 2026-10-21 | `75c42e59` | 0 |
| Vazia | `docs/manual/chapter-06-security-review-2026-10-21` | - | 2026-10-21 | `75c42e59` | 0 |
| Vazia | `docs/manual/chapter-06-seguranca-2026-10-21` | #308 merged | 2026-10-21 | `75c42e59` | 0 |
| Vazia | `docs/rgc-methodology-reconcile-2026-10-21` | - | 2026-10-21 | `a1fe33e7` | 0 |
| Vazia | `docs/status-rgc-refresh-2026-10-20-v2` | - | 2026-10-20 | `f6183062` | 0 |
| Vazia | `feat/r14-tenant-propagation` | - | 2026-10-03 | `2226e7c6` | 0 |
| Vazia | `fix/structured-access-logs` | - | 2026-10-17 | `b7a076f2` | 0 |
| Vazia | `fix/unify-tenant-context` | - | 2026-11-05 | `0b2d92f4` | 0 |
| Vazia | `security/distributed-rate-limit-adr` | - | 2026-11-05 | `0b2d92f4` | 0 |
| Vazia | `test/docs-markdown-integrity-2026-10-18` | - | 2026-10-17 | `2da10d55` | 0 |
| Incorporada | `docs/docker-curl-synthetic-demo` | #427 closed | 2026-11-04 | `05eeee96` | 1 |
| Incorporada | `docs/engineering-completion-roadmap` | #440 closed | 2026-11-06 | `aae85c21` | 2 |
| Incorporada | `docs/rgc-historical-status-clarification-2026-10-25` | #413 closed | 2026-10-26 | `53d31dd8` | 7 |
| Incorporada | `docs/status-v060-and-traceability-history` | #426 closed | 2026-11-04 | `5bf312a8` | 1 |
| Incorporada | `feat/report-json-schema` | #430 closed | 2026-11-05 | `c84203ac` | 5 |
| Incorporada | `fix/rgc-pilot-checker-duplicate-integrity` | #438 closed | 2026-11-06 | `fef06a7a` | 6 |
| Incorporada | `test/judge2-property-invariants` | #428 closed | 2026-11-04 | `5484c7c5` | 4 |
| Incorporada | `test/normative-rectification` | #429 closed | 2026-11-04 | `6b585d3d` | 2 |
| Incorporada | `test/offline-socket-blocked` | #424 closed | 2026-11-04 | `c64b0d0c` | 1 |
| Incorporada | `test/paraphrase-invariance-v1` | #423 closed | 2026-11-04 | `939aed71` | 2 |
| Conteúdo não incorporado | `chore/sanitize-benchmark-report-paths` | #498 closed | 2026-11-08 | `c50765a7` | 8 |
| Conteúdo não incorporado | `dependabot/pip/pandas-3.1.1` | #524 closed | 2026-11-11 | `5a2f5e1f` | 2 |
| Conteúdo não incorporado | `dependabot/pip/psutil-7.2.2` | #522 closed | 2026-11-11 | `74d71fd3` | 2 |
| Conteúdo não incorporado | `dependabot/pip/pyarrow-26.0.1` | #521 closed | 2026-11-11 | `bd308d01` | 2 |
| Conteúdo não incorporado | `dependabot/pip/safetensors-0.8.0` | #558 closed | 2026-11-15 | `c649d72c` | 1 |
| Conteúdo não incorporado | `dependabot/pip/transformers-5.22.2` | #519 closed | 2026-11-11 | `cc0c5ad2` | 4 |
| Conteúdo não incorporado | `docs/dec-026-proposal` | #509 closed | 2026-11-20 | `38d45419` | 4 |
| Conteúdo não incorporado | `docs/nucleo-estado` | #510 closed | 2026-11-08 | `54d811fa` | 1 |
| Conteúdo não incorporado | `docs/p2-ledger-eligibility-v0.9-2026-11-08` | #506 closed | 2026-11-08 | `fc4f8970` | 2 |
| Conteúdo não incorporado | `docs/p3-minicheck-flan-t5-protocol-2026-11-08` | #507 closed | 2026-11-20 | `7bb919e4` | 2 |
| Conteúdo não incorporado | `docs/rgc-continuity-2026-11-03` | #421 closed | 2026-11-04 | `a5b55eeb` | 2 |
| Conteúdo não incorporado | `docs/rgc-methodology-continuity-2026-10-22` | - | 2026-10-22 | `aae957eb` | 1 |
| Em conflito | `audit/e1-api-reliability-boundaries` | #441 closed | 2026-11-06 | `b5459156` | 1 |
| Em conflito | `chore/project-protection-and-provenance` | - | 2026-10-03 | `b3cb4477` | 1 |
| Em conflito | `ci/fix-cleanup-merged-branches` | #416 closed | 2026-11-02 | `6ee27fc2` | 8 |
| Em conflito | `ci/reproducible-distributions` | #415 closed | 2026-10-27 | `92103763` | 14 |
| Em conflito | `docs/dec-011-annotation-guide` | #206 merged | 2026-10-17 | `3a5d3717` | 2 |
| Em conflito | `docs/e3-confirm-dev-b-prereg` | #504 closed | 2026-11-11 | `1a71aa47` | 10 |
| Em conflito | `docs/index-navigation-2026-11-08` | #500 closed | 2026-11-08 | `05d8af6a` | 2 |
| Em conflito | `docs/readme-one-page-status` | #431 closed | 2026-11-04 | `561665c9` | 2 |
| Em conflito | `docs/release-provenance-v0.6.0-attachments` | #414 closed | 2026-10-26 | `ac6aa736` | 1 |
| Em conflito | `docs/rgc-amendment-consistency-2026-10-21` | #364 closed | 2026-10-21 | `ae204ee6` | 6 |
| Em conflito | `docs/rgc-amendments-consistency-2026-10-21` | - | 2026-10-21 | `e598affc` | 7 |
| Em conflito | `docs/rgc-current-preregistration-reading-2026-10-21-rebased` | #319 closed | 2026-10-21 | `d43ee016` | 2 |
| Em conflito | `docs/rgc-final-consistency-2026-10-21` | - | 2026-10-21 | `3cfbe566` | 1 |
| Em conflito | `docs/rgc-gate-templates` | #417 closed | 2026-11-04 | `eccd3769` | 31 |
| Em conflito | `docs/rgc-methodology-audit-2026-11-09` | #514 closed | 2026-11-11 | `764a3003` | 6 |
| Em conflito | `docs/rgc-methodology-audit-refresh-2026-11-12` | #531 closed | 2026-11-20 | `840e3162` | 4 |
| Em conflito | `docs/rgc-preregistration-reading-note-2026-10-21` | #310 closed | 2026-10-21 | `a8fa3bac` | 1 |
| Em conflito | `docs/rgc-statistics-reconciliation` | #553 closed | 2026-11-20 | `686647c4` | 3 |
| Em conflito | `docs/rgc-status-reconciliation-2026-11-08` | #512 closed | 2026-11-12 | `e95b07c9` | 9 |
| Em conflito | `docs/security-manual-refresh-2026-11-16` | #573 closed | 2026-11-16 | `ca72f3d9` | 2 |
| Em conflito | `docs/status-current-main-2026-11-05` | #436 closed | 2026-11-05 | `bfa8f7b1` | 2 |
| Em conflito | `docs/status-post-578-2026-11-17` | #579 closed | 2026-11-20 | `a11c8ecb` | 14 |
| Em conflito | `docs/status-refresh-2026-11-12` | #530 closed | 2026-11-12 | `4ca7a1c3` | 17 |
| Em conflito | `docs/status-release-clarity` | #422 closed | 2026-11-04 | `e6ad1067` | 2 |
| Em conflito | `docs/status-release-final-2026-10-21` | - | 2026-10-21 | `90bd57ac` | 3 |
| Em conflito | `docs/status-v06-final-2026-10-21-final2` | - | 2026-10-21 | `11e335c7` | 2 |
| Em conflito | `eval/dec-018-hidden-confirmatory-partition-2026-10-21-final` | #340 closed | 2026-10-21 | `92078cbf` | 8 |
| Em conflito | `eval/dec-019-article-cluster-bootstrap-2026-10-21` | #330 closed | 2026-10-21 | `3d0327c5` | 12 |
| Em conflito | `eval/dec-019-article-cluster-bootstrap-2026-10-21-rebased` | #348 closed | 2026-10-21 | `51ac00c4` | 10 |
| Em conflito | `eval/dec-020-kappa-criteria-2026-10-21` | - | 2026-10-21 | `64fdf54c` | 8 |
| Em conflito | `eval/rgc-pilot` | - | 2026-10-13 | `40f89fc8` | 2 |
| Em conflito | `feat/diagnostic-failure-stage` | #425 closed | 2026-11-04 | `8eadd9ad` | 2 |
| Em conflito | `feat/diagnostic-stage-reapply` | #456 closed | 2026-11-06 | `c26eb6aa` | 16 |
| Em conflito | `feat/e3-confirm-dev-b` | #505 closed | 2026-11-11 | `7b4d19d3` | 57 |
| Em conflito | `feat/rgc-annotation-approval-gate` | - | 2026-10-21 | `cb3bf9cd` | 21 |
| Em conflito | `feat/rgc-run-manifest` | #554 closed | 2026-11-17 | `3bc23ba2` | 19 |
| Em conflito | `fix/api-rate-limit-isolation-proxy-contract` | #444 closed | 2026-11-06 | `e79e8332` | 23 |
| Em conflito | `fix/p1-workflow-lock-governance-2026-11-11` | #517 closed | 2026-11-11 | `804f3892` | 115 |
| Em conflito | `fix/p1-workflow-lock-governance-rebased-2026-11-11` | #527 closed | 2026-11-12 | `7bd25aa4` | 70 |
| Em conflito | `fix/rgc-approval-gate-integrity` | #420 closed | 2026-11-04 | `fe748251` | 30 |
| Em conflito | `fix/rgc-cluster-citation-consistency` | #432 closed | 2026-11-05 | `6477f57a` | 7 |
| Em conflito | `fix/rgc-pilot-source-id-duplicates` | #437 closed | 2026-11-05 | `6ee8cc2d` | 3 |
| Em conflito | `fix/scale-words-golden-v01` | #571 closed | 2026-11-20 | `874fad88` | 6 |
| Em conflito | `q3-q5-resource-lifecycle-cli` | - | 2026-10-11 | `f613bf2a` | 6 |
| Em conflito | `r1-a-strict-verification-models-2026-09-30` | - | 2026-09-30 | `d5af0373` | 4 |
| Em conflito | `release/align-v0.6.0-date-2026-10-25` | #404 closed | 2026-10-25 | `f67eafca` | 4 |
| Em conflito | `release/v0.5.0` | #170 merged | 2026-10-13 | `7cb6f82d` | 4 |
| Em conflito | `repro/phase1b-dev-env-2026-11-12` | #535 closed | 2026-11-13 | `0edc35b9` | 27 |
| Em conflito | `security/audit-full-nli-dependency-environment-2026-11-11` | #528 closed | 2026-11-12 | `4dfdf162` | 24 |
| Em conflito | `security/enforce-dependency-audit-gates-2026-11-11` | #529 closed | 2026-11-12 | `821af12e` | 17 |
| Em conflito | `security/nli-pyarrow-clean-2026-11-12` | #534 closed | 2026-11-12 | `2dd5a044` | 6 |
| Em conflito | `transplant/417-own-delta` | #455 closed | 2026-11-06 | `99b380ee` | 6 |
| Em conflito | `transplant/420-copy` | #451 closed | 2026-11-06 | `fe2afa26` | 2 |
| Em conflito | `transplant/425-reapply` | #458 closed | 2026-11-06 | `b6fdfced` | 1 |
| Em conflito | `transplant/432-reapply` | #453 closed | 2026-11-06 | `f2dc86fe` | 1 |
| Em conflito | `transplant/grupo-1` | #447 closed | 2026-11-06 | `6b373806` | 12 |
