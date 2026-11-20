Revisão por ferramenta automatizada, publicada pelo mantenedor.

# Inventário e matriz de rastreabilidade — 2026-11-20

- **Consulta:** 2026-11-20T18:32:36Z. **`main`:** `1abe7eaa4ce7c6b6823f0f10646b9ee698487d3d` (merge da #589).
- **PRs:** 583 no total (#1–#595; os números que faltam são issues): 24 abertas, 431 mescladas, 128 fechadas sem merge. A listagem foi paginada até o fim.
- **Método das fechadas sem merge:** o diff de cada PR (merge-base até o head, por `refs/pull/N/head`) é aplicado ao contrário sobre a `main` (`git apply -R --check`). Aplica = PRESENTE; aplica no sentido normal = AUSENTE; nenhum dos dois = DIVERGENTE. Nas divergentes, contou-se a fração das linhas acrescentadas (>12 caracteres) que existem hoje no arquivo correspondente da `main`. O destino final de cada uma foi conferido no código quando a contagem não bastava.
- **Método das mescladas:** `git merge-base --is-ancestor <merge_commit> origin/main`.
- **Estados:** os da especificação do mantenedor (INTEGRADO, IMPLEMENTADO EM PR ABERTA, DUPLICADO/SUBSTITUÍDO, FECHADO SEM MERGE — RESOLVIDO/PENDENTE, BLOQUEADO POR DECISÃO, OBSOLETO COM JUSTIFICATIVA, NÃO VERIFICADO; nenhuma PR terminou neste estado). Nenhuma PR foi fechada e nenhuma branch foi apagada.

## 1. PRs abertas (24)

| PR | Título | Base | Head | Checks (ok/total) | Merge | Estado técnico | Dependências | Prioridade | Ação | Evidência |
|---|---|---|---|---|---|---|---|---|---|---|
| #595 | docs(status): estado real da main em 2026-11-20, auditoria técnica e proposta de POC | main | `a885c6f` | 20/20 | clean | IMPLEMENTADO EM PR ABERTA | por último (STATUS no SHA final) | P2 | Aguarda autorização de merge | STATUS, auditoria, POC e este inventário. |
| #594 | feat(audit): rotação de chave HMAC sem invalidar os rastros antigos — P2 | main | `db228d3` | 37/37 | clean | IMPLEMENTADO EM PR ABERTA | conflito textual com #590 (manual 05) | P2 | Aguarda autorização de merge | Rotação HMAC; 4 testes; mutação 3/3; integração com r2-v4 verificada. |
| #593 | fix(security): erros de provider não expõem URLs internas ao cliente — P2 | main | `40105d8` | 37/37 | clean | IMPLEMENTADO EM PR ABERTA | — | P2 | Aguarda autorização de merge | Erros sem URL interna; 10 testes; mutação 2/2. |
| #592 | fix(stance): pergunta, condição, meta e retificação não confirmam a afirmação (detector v12) — P1 | main | `e92370c` | 37/37 | clean | IMPLEMENTADO EM PR ABERTA | conflito de versão com #571 | P1 | Aguarda autorização de merge | Detector v12; 19 testes; mutação 8/8 + 4/4. |
| #591 | fix(search): cada resultado de busca é uma fonte própria, com proveniência — P1 | main | `d20a202` | 38/38 | clean | IMPLEMENTADO EM PR ABERTA | — | P1 | Aguarda autorização de merge | Uma fonte por resultado; 8 testes; mutação 6/6. |
| #590 | fix(audit): o rastro do /v2/audit vincula a adjudicação devolvida (r2-v4) — P1 | main | `213aaf0` | 38/38 | clean | IMPLEMENTADO EM PR ABERTA | — | P1 | Aguarda autorização de merge | Rastro r2-v4 com adjudication_sha256; 15 testes; mutação 4/4. |
| #584 | fix(rgc): isolate snapshot runner from Python environment injection | fix/rgc-e5-immutable-snapshots | `6af29f7` | 13/13 | clean | IMPLEMENTADO EM PR ABERTA | empilhada sobre #580 | P1 | Revisão humana independente | Isolamento do filho; brecha de variáveis forjadas corrigida (6af29f7). |
| #583 | docs(rgc): reconcile statistical specification with DEC-027 | main | `dedc06c` | 20/20 | clean | BLOQUEADO POR DECISÃO | conflita com #531 em STATISTICS.md | P2 | Decisão metodológica | Reconciliação STATISTICS.md × DEC-027; substitui #553. |
| #581 | docs(audit): revalidate RGC methodology checkpoint 2026-11-17 | main | `cae8dbc` | 20/20 | clean | BLOQUEADO POR DECISÃO | — | P3 | Decisão do mantenedor | Registro de checkpoint metodológico de 2026-11-17. |
| #580 | fix(rgc): bind E5 to immutable input snapshots | main | `53344fa` | 21/21 | clean | IMPLEMENTADO EM PR ABERTA | base de #584 | P1 | Revisão humana independente (900 linhas não revisadas linha a linha) | E5: snapshots, manifesto, publicação atômica; 219 testes do runner. |
| #579 | docs(status): record PR #578 integration and post-merge CI | main | `a11c8ec` | 20/20 | clean | OBSOLETO COM JUSTIFICATIVA | superada por #595 | P3 | Recomendar fechamento ao mantenedor | Snapshot de status de 2026-11-17 já substituído. |
| #577 | fix(rgc): enforce informative-component resolution in H1 | main | `f3cde1a` | 21/21 | clean | IMPLEMENTADO EM PR ABERTA | — | P1 | Revisão humana independente | Gate H1 com resolução do sign-flip; revisado: correto. |
| #576 | fix(rgc): bind agreement metrics to annotation snapshots | main | `346d060` | 21/21 | clean | IMPLEMENTADO EM PR ABERTA | — | P1 | Revisão humana independente | Concordância lida de um snapshot de bytes; revisado: correto. |
| #571 | fix(stance): escala sem moeda e contagens com escala (detector v11) — muda a referência do Golden v0.1, requer aprovação | main | `874fad8` | 20/20 | clean | BLOQUEADO POR DECISÃO | conflito de versão com #592; congelamento RGC vincula stance.py | P1 | Aprovação metodológica do Golden v0.1 | Só x02 muda (PARTIALLY→CONFLICTING, igual à referência); digest 1fd6fdb7… |
| #554 | feat(rgc): freeze binds every statistical module; run manifest per execution (E5) | main | `3bc23ba` | 0/0 | dirty | DUPLICADO/SUBSTITUÍDO | substituída por #580 | P3 | Recomendar fechamento ao mantenedor | Funções e vínculos portados para a #580 (rgc_random, verify_run_manifest, primary_unit); sobra só redação e versão. |
| #553 | docs(rgc): reconcile STATISTICS.md with DEC-027 and the implemented runner | main | `686647c` | 21/21 | clean | DUPLICADO/SUBSTITUÍDO | substituída por #583 | P3 | Recomendar fechamento ao mantenedor | 53/53 linhas presentes na #583. |
| #539 | docs(audit): record RGC methodology continuity findings | main | `46af4ff` | 21/21 | clean | BLOQUEADO POR DECISÃO | — | P3 | Decisão do mantenedor | Registro histórico de continuidade (2026-11-13). |
| #535 | feat(repro): record and enforce the historical Phase 1b DEV environment | main | `0edc35b` | 20/21 (falha: dependency-review) | dirty | BLOQUEADO POR DECISÃO | conflito em workflows | P2 | Decisão sobre alertas do nltk 3.9.4 e pins históricos | dependency-review falha. |
| #531 | docs(rgc): reconcile component identity and methodology audit | main | `840e316` | 21/21 | clean | BLOQUEADO POR DECISÃO | conflita com #583 | P2 | Refazer sobre a #583 ou fechar | Identidade de componente (DEC-023). |
| #527 | fix(benchmarks): govern P1 workflow and one-shot lock | feat/e3-confirm-dev-b | `7bd25aa` | 21/21 | clean | BLOQUEADO POR DECISÃO | empilhada sobre #505 | P2 | Depende da #505 | Governança do lock P1. |
| #509 | docs(benchmarks): DEC-026 proposal and 55-cell eligibility reconciliation | main | `38d4541` | 21/21 | clean | BLOQUEADO POR DECISÃO | — | P3 | Decisão do mantenedor | Proposta DEC-026. |
| #507 | docs(benchmarks): propose MiniCheck-Flan-T5-Large protocol | main | `7bb919e` | 21/21 | clean | BLOQUEADO POR DECISÃO | — | P3 | Decisão do mantenedor | Proposta de protocolo MiniCheck; sem download de pesos. |
| #505 | feat(benchmarks): P1 single DEV-B confirmation of E3b-01 (document-cluster bootstrap) | main | `7b4d19d` | 20/20 | dirty | BLOQUEADO POR DECISÃO | conflito em DECISIONS-PENDING.md; base de #527 | P2 | Autorização de execução DEV-B | Execução única não autorizada. |
| #504 | benchmarks: DEC-025, proposed E3 preregistration and reproducible LTT planning helper | main | `1a71aa4` | 20/20 | dirty | BLOQUEADO POR DECISÃO | conflito em DECISIONS-PENDING.md | P2 | Decisão sobre pré-registro E3 | Pré-registro. |

## 2. Grafo de dependências e sobreposições (verificado)

- **Empilhadas:** #584 → #580 → main; #527 → #505 → main. O `ci.yml` só dispara em PRs com base na `main`, então as empilhadas não têm CI automático; a #584 foi validada por `workflow_dispatch` (CI, Security e Simulação RGC: 13/13 jobs verdes no `6af29f7`).
- **Substituições comprovadas por conteúdo:** #553 → #583 (53/53 linhas); #554 → #580 (funções e vínculos portados); #579 → #595; #517 → #527; #514 → #531; #573 → #574 (mesclada).
- **Conflitos entre abertas:** #571 × #592 (versão do detector); #590 × #594 (`docs/manual/05-operacao.md`, resolvido numa integração local); #531 × #583 (`docs/eval/STATISTICS.md`, texto normativo).
- **Acoplamento com o congelamento RGC:** o manifesto da #580 vincula `verification/stance.py`; a #571 e a #592 precisam ser decididas antes do congelamento.
- **Integração da Fase 1 (local):** main + #590 + #591 + #592 + #593 + #594 → 2437 testes, ruff e mypy limpos, digests do Golden iguais aos da `main`; rotação HMAC (#594) verificada sobre rastros r2-v4 (#590).
- **Integração RGC (local):** main + #580 + #584 + #576 + #577 → 2452 testes em 3.11/3.12/3.13, `mypy --strict` limpo; sem congelamento, o runner sai com código 2.

## 3. PRs fechadas sem merge (128)

| PR | Título | Verificação automática | Estado técnico | Justificativa |
|---|---|---|---|---|
| #1 | build(deps): bump actions/checkout from 4 to 7 | AUSENTE(<=20%) (0/9 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #2 | build(deps): bump actions/setup-python from 5 to 7 | AUSENTE(<=20%) (0/8 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #3 | chore(deps-dev): update pytest-cov requirement from <7,>=6 to >=6,<8 | AUSENTE(<=20%) (0/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Faixas de pytest/pytest-cov redefinidas depois no pyproject. |
| #4 | chore(deps-dev): update pytest requirement from <9,>=8.3 to >=8.3,<10 | AUSENTE(<=20%) (0/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Faixas de pytest/pytest-cov redefinidas depois no pyproject. |
| #5 | build(deps-dev): update mypy requirement from <2,>=1.17 to >=1.17,<3 | INCORPORADO(>=90%) (1/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #6 | chore(deps): bump github/codeql-action from 3 to 4 | AUSENTE(<=20%) (0/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #29 | feat(r1-b): add deterministic evidence cluster independence | INCORPORADO(>=90%) (121/132 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #30 | feat(r1-c): add deterministic numeric and date verification | INCORPORADO(>=90%) (274/291 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #37 | feat: consolidate ATTRACTOR operational verification | AUSENTE(<=20%) (46/369 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Pipeline de verificação evoluiu por PRs posteriores; conteúdo parcialmente reescrito. |
| #51 | feat: start R4 content-addressed replay persistence | INCORPORADO(>=90%) (136/149 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #54 | feat: enforce grounded synthesis gate | INCORPORADO(>=90%) (38/42 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #56 | feat: add R7 deterministic red-team corpus | PARCIAL (62/78 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Red-team e job store existem na main (redteam.py, job_store.py). |
| #58 | feat: add R9 durable job state | PARCIAL (175/210 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Red-team e job store existem na main (redteam.py, job_store.py). |
| #69 | feat: add deterministic comparative evaluation arena | AUSENTE_DA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Módulo arena existe (src/ayorai_attractor/arena.py). |
| #85 | feat: P0 pipeline contracts + official Golden runner | PARCIAL (614/1180 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Pipeline de verificação evoluiu por PRs posteriores; conteúdo parcialmente reescrito. |
| #86 | fix(f0): stabilize claim pipeline and CI gates | PARCIAL (405/767 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Pipeline de verificação evoluiu por PRs posteriores; conteúdo parcialmente reescrito. |
| #87 | fix(f0): recover claim-as-input verification pipeline | PARCIAL (671/990 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Pipeline de verificação evoluiu por PRs posteriores; conteúdo parcialmente reescrito. |
| #92 | audit: E4 quality checks without rerunning E3 | INCORPORADO(>=90%) (2545/2769 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #105 | chore(deps-dev): update transformers requirement from <5,>=4.55 to >=4.55,<6 | INCORPORADO(>=90%) (1/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #142 | test: enforce deterministic verdict authority boundaries | PARCIAL (102/160 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Guardas de autoridade do veredito testadas em 35 arquivos de teste da main. |
| #155 | docs: refresh public metadata after v0.4.0 | AUSENTE(<=20%) (2/23 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #187 | build(deps): bump github/codeql-action/init from 4.38.2 to 4.38.3 | AUSENTE(<=20%) (0/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #188 | build(deps): bump github/codeql-action/analyze from 4.38.2 to 4.38.3 | AUSENTE(<=20%) (0/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #191 | build(deps): bump github/codeql-action/autobuild from 4.38.2 to 4.38.3 | AUSENTE(<=20%) (0/1 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #202 | build(deps): bump the codeql-action group with 3 updates | AUSENTE(<=20%) (0/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #235 | docs: reconcile status and changelog after PR 229 | AUSENTE(<=20%) (0/19 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #237 | feat(rgc-eval): report rectification strata | PARCIAL (31/83 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Estrato retificado (campo rectified, strata.rectified) implementado no runner da main. |
| #238 | docs: disambiguate release decision identifiers | AUSENTE(<=20%) (0/8 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #239 | docs: clarify approved and pending decision register | AUSENTE_DA_MAIN | FECHADO SEM MERGE, PROBLEMA PENDENTE | Escopo dos registros de decisão: decisões RGC aprovadas (DEC-017..020, 023, 027) seguem só em DECISIONS-PENDING.md, não em DECISIONS-APPROVED.md. |
| #240 | feat(rgc-eval): report rectification strata | PARCIAL (31/83 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Estrato retificado (campo rectified, strata.rectified) implementado no runner da main. |
| #265 | docs: document deterministic Judge rules and traceability | INCORPORADO(>=90%) (418/426 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #269 | docs: review RGC PT-BR benchmark methodology | INCORPORADO(>=90%) (99/103 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #272 | docs: review RGC PT-BR benchmark methodology | INCORPORADO(>=90%) (93/97 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #276 | fix: preserve frozen r1-a null-body response | INCORPORADO(>=90%) (11/12 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #277 | docs(eval): registrar proposta datada de emenda DEC-014 | AUSENTE_DA_MAIN | OBSOLETO COM JUSTIFICATIVA | Proposta de emenda DEC-014 de 2026-10-20; emendas posteriores registradas no pré-registro. |
| #282 | build(deps): bump the codeql-action group with 3 updates | AUSENTE(<=20%) (0/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Actions atualizadas depois por outras PRs; a main fixa actions por SHA (checkout v7.0.1, codeql atual). |
| #283 | docs(status): refresh RGC test and governance snapshot | AUSENTE(<=20%) (1/11 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #285 | docs(governance): record maintainer authorization DEC-016 | INCORPORADO(>=90%) (12/13 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #287 | docs(eval): incorporate RGC baseline B amendment 6 | PARCIAL (8/9 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Notas de leitura do pré-registro e cabeçalhos de decisão incorporados por PRs posteriores. |
| #290 | test(api): clarify frozen r1-a null-body contract drift | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #298 | docs(eval): link missing-versus-invalid contract to DEC-017 | PARCIAL (9/13 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #307 | docs(manual): add chapter 05 on operation and CLI | PARCIAL (21/74 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Capítulo 05 do manual existe (docs/manual/05-operacao.md). |
| #310 | docs(rgc): clarify current preregistration reading | DIFF_VAZIO | OBSOLETO COM JUSTIFICATIVA | Diff vazio em relação à base. |
| #312 | docs(decisions): normalize DEC-016 and DEC-017 headings | INCORPORADO(>=90%) (3/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #313 | docs(rgc): clarify current preregistration reading | PARCIAL (2/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Notas de leitura do pré-registro e cabeçalhos de decisão incorporados por PRs posteriores. |
| #315 | docs(decisions): normalize DEC-016 and DEC-017 headings | PARCIAL (2/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Notas de leitura do pré-registro e cabeçalhos de decisão incorporados por PRs posteriores. |
| #317 | eval(rgc): approve DEC-017 invalid-prediction handling | PARCIAL (20/36 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #318 | docs(rgc): clarify current preregistration reading | PARCIAL (2/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Notas de leitura do pré-registro e cabeçalhos de decisão incorporados por PRs posteriores. |
| #319 | docs(rgc): clarify current preregistration reading | AUSENTE(<=20%) (0/2 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Notas de leitura do pré-registro e cabeçalhos de decisão incorporados por PRs posteriores. |
| #321 | eval(rgc): approve DEC-017 invalid-prediction handling | PARCIAL (28/42 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #322 | docs(rgc): clarify current preregistration reading | AUSENTE(<=20%) (0/3 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Notas de leitura do pré-registro e cabeçalhos de decisão incorporados por PRs posteriores. |
| #324 | test(providers): cover OpenAI-compatible error paths | PARCIAL (13/32 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Os três cenários (erro de URL, resposta malformada, URL sem HTTPS) estão testados na main: tests/test_provider_contracts.py e tests/test_provider_configuration.py. |
| #325 | test(api): isolate null-body validation across dependency versions | INCORPORADO(>=90%) (81/88 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #327 | test(api): record controlled null-body dependency reproduction | INCORPORADO(>=90%) (81/89 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #328 | test(api): record controlled null-body dependency reproduction | INCORPORADO(>=90%) (81/89 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #329 | fix(governance): restore DEC-017 as pending | PARCIAL (14/23 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #330 | eval(rgc): make article-cluster bootstrap primary | PARCIAL (96/123 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #332 | test(api): record controlled null-body dependency reproduction | INCORPORADO(>=90%) (81/89 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #334 | eval(rgc): restore approved DEC-018 hidden partition scope | PARCIAL (49/55 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #336 | test(api): record controlled null-body dependency reproduction | INCORPORADO(>=90%) (81/89 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #338 | eval(rgc): approve DEC-018 hidden-only H1 | PARCIAL (13/32 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #340 | eval(rgc): approve DEC-018 hidden-only H1 | PARCIAL (13/36 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #341 | docs(manual): add chapter 08 on evaluation | INCORPORADO(>=90%) (37/39 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #343 | eval(rgc): approve DEC-018 hidden-only H1 | PARCIAL (21/45 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #344 | docs(manual): add chapter 08 on evaluation | INCORPORADO(>=90%) (37/39 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #346 | docs(manual): add chapter 08 on evaluation | DIFF_VAZIO | OBSOLETO COM JUSTIFICATIVA | Diff vazio em relação à base. |
| #347 | eval(rgc): implement DEC-019 article-cluster bootstrap | PARCIAL (74/123 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #348 | eval(rgc): implement DEC-019 article-cluster bootstrap | PARCIAL (74/123 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #350 | eval(annotation): approve DEC-020 kappa agreement criterion | AUSENTE(<=20%) (5/157 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #364 | docs(rgc): mark superseded decision notes | INCORPORADO(>=90%) (5/5 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #367 | security: document rationale for nosec suppressions | AUSENTE(<=20%) (1/5 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | As duas supressões `# nosec B311` da main têm justificativa (stats.py, na linha anterior; international.py, na mesma linha). |
| #368 | docs(rgc): mark superseded DEC-017/018 notes as historical | PARCIAL (5/7 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Tentativas das DEC-017..020; decisões aprovadas e implementadas por PRs posteriores (registradas em DECISIONS-PENDING.md como 'Estado vigente: Aprovada'). |
| #371 | docs(status): reconcile RGC evidence and v0.6.0 draft | AUSENTE(<=20%) (0/8 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #372 | security: document rationale for nosec suppressions | AUSENTE(<=20%) (0/5 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | As duas supressões `# nosec B311` da main têm justificativa (stats.py, na linha anterior; international.py, na mesma linha). |
| #392 | docs(audit): record verified project continuity state | AUSENTE_DA_MAIN | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #403 | docs: refresh RGC methodology continuity and current status | PARCIAL (60/111 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #404 | release: align v0.6.0 date and artifact publication gate | AUSENTE(<=20%) (0/12 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Data da v0.6.0 alinhada pelas #405 e #406. |
| #413 | docs(rgc): clarify superseded decision proposals | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #414 | docs(release): record v0.6.0 attachments and build attempts | PARCIAL (7/8 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Proveniência da v0.6.0 registrada em docs/release/RELEASE-PROVENANCE.md. |
| #415 | ci(build): make distribution builds reproducible and attempt-scoped | INCORPORADO(>=90%) (354/354 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #416 | fix(ci): guard merged branch cleanup eligibility | INCORPORADO(>=90%) (135/135 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #417 | docs(rgc): add blank templates for human evaluation gates | INCORPORADO(>=90%) (158/158 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #420 | fix(rgc): bind annotation IDs and reject hidden RULE_GAP | INCORPORADO(>=90%) (394/396 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #421 | docs(audit): record RGC methodology checkpoint 2026-11-03 | AUSENTE_DA_MAIN | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #422 | docs(status): align release and historical traceability references | AUSENTE(<=20%) (2/10 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #423 | test(verification): add synthetic paraphrase invariance regression | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #424 | test(verification): verify offline pipeline with sockets blocked | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #425 | feat(diagnostics): report verification failure stage | INCORPORADO(>=90%) (155/158 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #426 | docs(status): align current release and traceability sources | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #427 | docs(readme): add Docker and curl verification demo | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #428 | test(judge2): add property invariants for canonical adjudication | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #429 | test(rgc): add synthetic normative rectification invariant | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #430 | feat(golden): publish versioned evaluation report JSON Schema | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #431 | docs(readme): add one-page project status summary | AUSENTE(<=20%) (0/4 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #432 | fix(rgc): validate cluster IDs against cited articles | PARCIAL (100/116 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Validação cited_article_ids/bootstrap_cluster_id existe no runner da main. |
| #436 | docs(status): record verified main and PR checks | AUSENTE(<=20%) (0/21 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #437 | fix(rgc): reject duplicate and malformed pilot source records | PARCIAL (14/26 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Documento-fonte duplicado é recusado pelo runner (load_documents). |
| #438 | fix(rgc): preserve duplicate annotation integrity | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #440 | docs(engineering): establish software completion roadmap | PRESENTE_NA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #441 | docs(audit): record E1 API reliability and security boundaries | INCORPORADO(>=90%) (71/71 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #444 | fix(api): isolate rate limiters and document 429/proxy trust | INCORPORADO(>=90%) (268/277 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #447 | chore: transplante do Grupo 1 da consolidação (#428, #429, #430, #416, #417, #440, #441, #413, #414, #426, #438, #423) | INCORPORADO(>=90%) (1221/1223 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #451 | fix(rgc): transplant annotation integrity gate from #420 | INCORPORADO(>=90%) (394/396 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #453 | fix(rgc): validate cluster IDs against cited articles | PARCIAL (100/116 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Transplante de #432; validação de IDs de cluster contra artigos citados existe no runner. |
| #455 | docs(rgc): transplant only own delta from stacked #417 | INCORPORADO(>=90%) (158/158 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #456 | feat(diagnostics): reapply optional failure stage with null init semantics | INCORPORADO(>=90%) (169/170 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #458 | feat(diagnostics): report verification failure stage | PARCIAL (155/197 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Estágio de falha (FailureStage) existe na main. |
| #498 | chore(reports): sanitize ephemeral benchmark workspace paths | INCORPORADO(>=90%) (486/512 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #500 | docs(index): clarify current documentation and archive candidates | AUSENTE(<=20%) (1/50 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #506 | docs(benchmarks): propose ledger-derived E3 eligibility v0.9 | AUSENTE_DA_MAIN | OBSOLETO COM JUSTIFICATIVA | Proposta de elegibilidade v0.9 sucedida pela reconciliação de 55 células (#509, aberta). |
| #510 | docs(project): núcleo state, evidence inventory and pending decisions (stage 0) | AUSENTE_DA_MAIN | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #512 | docs(status): record RGC methodology reconciliation blockers | AUSENTE(<=20%) (0/15 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #514 | docs(rgc): align component identity and record methodology audit | AUSENTE_DA_MAIN | DUPLICADO/SUBSTITUÍDO | Reaplicada como #531 (aberta). |
| #517 | fix(benchmarks): govern P1 workflow and one-shot lock | AUSENTE(<=20%) (77/392 linhas) | DUPLICADO/SUBSTITUÍDO | Reaplicada como #527 (aberta, empilhada sobre #505). |
| #519 | build(deps): bump transformers from 4.55.4 to 5.22.2 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #521 | build(deps): bump pyarrow from 21.0.0 to 26.0.1 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #522 | build(deps): bump psutil from 7.0.0 to 7.2.2 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #523 | build(deps): bump numpy from 2.2.6 to 2.5.4 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #524 | build(deps): bump pandas from 2.3.2 to 3.1.1 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #528 | security(ci): audit full NLI and benchmark dependency environment | PARCIAL (84/94 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Ambiente NLI auditado integrado pela #536. |
| #529 | security(ci): enforce strict dependency audit gates | INCORPORADO(>=90%) (43/44 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Conteúdo presente na main. |
| #530 | docs(status): refresh project status and RGC gates | AUSENTE(<=20%) (0/16 linhas) | OBSOLETO COM JUSTIFICATIVA | Atualização de status/índice/continuidade superada por versões posteriores de STATUS.md e registros de auditoria. |
| #534 | security(deps): harden PyArrow and full NLI dependency environment | PARCIAL (86/97 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Ambiente NLI auditado integrado pela #536. |
| #557 | build(deps): bump python from 3.12-slim to 3.15-slim in /docker | AUSENTE_DA_MAIN | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Política do Dependabot (#567): a imagem não sobe de linha de Python sem decisão. |
| #558 | build(deps): bump safetensors from 0.6.2 to 0.8.0 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #559 | build(deps): bump accelerate from 1.10.1 to 1.15.0 | AUSENTE_DA_MAIN | BLOQUEADO POR DECISÃO | Pins históricos de requirements-benchmark-pilot.txt preservados de propósito (#567); avisos de segurança conhecidos continuam (achado P3-1). |
| #560 | build(deps): bump huggingface-hub from 0.34.4 to 2.4.0 | AUSENTE(<=20%) (0/2 linhas) | FECHADO SEM MERGE, PROBLEMA RESOLVIDO | Ambiente NLI auditado com huggingface-hub 1.32 (#536). |
| #573 | docs(security): document audit integrity and admission controls | PARCIAL (24/30 linhas) | DUPLICADO/SUBSTITUÍDO | Mesmo conteúdo integrado pela #574. |

## 4. PRs mescladas (431)

Todas as 425 PRs mescladas com base `main` têm o commit de merge no histórico da `main`. As seis com outra base: #487 e #543 (`gh-pages`, site); #13 e #90 (base intermediária, commits na `main`); #166 e #168 (base intermediária integrada depois por squash; conteúdo da #168 presente na `main` ≥90%, a #166 é auxiliar de merge). O CI pós-merge da `main` atual (CI, Security, CodeQL) está verde; não houve reexecução individual dos testes de cada PR histórica.

| PR | Título | Commit de merge |
|---|---|---|
| #7 | A1: isolate AYORAI ATTRACTOR namespace | `5b00518` |
| #8 | A2: CI coverage baseline and ratchet | `de31bab` |
| #9 | A2.1: enforce true monotonic coverage ratchet | `46873e3` |
| #10 | A2.2: publish verified coverage map | `8662700` |
| #11 | A3: establish strict mypy ratchet | `db5d66e` |
| #12 | A4: golden set v0 and human review draft | `b7df480` |
| #13 | A4: deterministic golden baseline runner | `e1d3ec3` |
| #14 | docs: close Phase 0 with verified baseline and milestones | `f31f615` |
| #21 | community: add contribution docs and starter issues | `ad18d1e` |
| #22 | docs: restructure ATTRACTOR portfolio README | `9c42c22` |
| #23 | docs: add post-R1 launch draft | `b42cadd` |
| #24 | docs: refresh verified progress after Phase 0 portfolio track | `8a27878` |
| #25 | docs(adr): accept ADR-002 after maintainer approval | `2ff8aac` |
| #26 | docs: record Master Gate completion | `1e1fc22` |
| #27 | feat(r1-a): add strict verification model contracts | `2a22832` |
| #28 | fix(r1-a): satisfy Ruff UP017 | `fb1361b` |
| #31 | feat(r1): complete deterministic verification engine | `04d6e25` |
| #32 | feat(r2): add deterministic Audit Mode report | `627373d` |
| #33 | feat(r3-r4): add deterministic Council and replay cores | `526fe0d` |
| #34 | feat: add deterministic R5-R10 and governance cores | `4a90ce5` |
| #35 | feat(r9): add durable workflow checkpoint core | `1362191` |
| #36 | fix: restore R1 numeric and response contracts | `5453f9a` |
| #38 | feat(r2): expose deterministic audit API | `32bf39d` |
| #39 | feat(r1a): expose strict deterministic verification API | `1968041` |
| #40 | feat(r1b): add deterministic Judge regression suite | `2c2878d` |
| #41 | test: add property-based evidence graph invariants | `3b290d1` |
| #42 | test: add provider capability contracts | `cc79bff` |
| #43 | docs(eval): document local reproducible evaluation | `88d9706` |
| #44 | test: cover Failure Engine edge cases | `218f994` |
| #45 | test: improve OpenSearch provider coverage | `9d8b253` |
| #46 | eval: add Golden v1 provenance edge case | `f5c1fae` |
| #47 | docs: align README with current verification state | `da584b4` |
| #48 | feat: close deterministic evaluation layer | `a37742d` |
| #49 | feat: persist R2 audit traces | `26d2935` |
| #50 | feat: integrate R3 council adapters | `4f59db7` |
| #52 | feat: add R4 content-addressed replay store | `bd78bd5` |
| #53 | feat: integrate R5 hybrid OpenSearch retrieval | `d62e827` |
| #55 | feat: enforce grounded synthesis gate | `ba82f28` |
| #57 | feat: add R8 deterministic observability metrics | `628791f` |
| #59 | feat: complete R10 comparative arena reporting | `8d8dfce` |
| #60 | feat: add R11 deterministic optimization core | `3014589` |
| #61 | docs: complete R12 governed MCP boundary | `a3cb90f` |
| #62 | feat: add R13 tenant isolation foundation | `4042d3c` |
| #63 | feat: add R9 durable job state | `6b9e40c` |
| #64 | feat: add R7 deterministic red-team corpus | `bfd2337` |
| #65 | feat: integrate deterministic verification pipeline | `04bbb4d` |
| #66 | feat: make R9 job state restart-safe with leases | `30997be` |
| #67 | feat: add deterministic Prometheus metrics export | `1d89397` |
| #68 | fix: remove obsolete golden runner canary | `223942a` |
| #70 | feat: add immutable tenant isolation context | `2b9c658` |
| #71 | feat: add bounded candidate optimization primitive | `335fb5e` |
| #72 | feat(r14): add provider-neutral tracing context | `c3ef2b0` |
| #73 | feat(r15): integrate durable jobs with worker executor | `7067a7e` |
| #74 | chore: harden supply-chain controls | `bc47937` |
| #75 | feat: add provider-neutral trace export boundary | `1d8e1ee` |
| #76 | R18: propagate trusted tenant context through runtime | `1088354` |
| #77 | R19: make evaluation reports JSON-ready and deterministic | `48a9a78` |
| #78 | R20: add semantic digest to Golden evaluation reports | `55bc8d7` |
| #79 | fix: restore golden fixture provider newlines | `994a082` |
| #80 | docs: record R19 and R20 evidence | `26f02cc` |
| #81 | feat: add optional OpenTelemetry trace sink | `0bc2188` |
| #82 | fix: make Golden abstention reporting contract-honest | `a6efd67` |
| #83 | chore: update dependency review action to v5 | `e2f0677` |
| #84 | security: publish CycloneDX SBOM artifact | `434ae40` |
| #88 | fix(f0): recover claim-as-input verification pipeline | `477308b` |
| #89 | docs: authorship and project governance | `0d8b984` |
| #90 | chore(authorship): merge current main into authorship branch | `75cd625` |
| #91 | feat(f1): multilingual hybrid stance engine | `f4445e0` |
| #94 | docs: add ATTRACTOR threat model | `b22a5f7` |
| #95 | fix: enforce replay digest integrity | `c7bf837` |
| #96 | fix: pin GitHub Actions by SHA | `1a71d55` |
| #97 | chore: integrity gates | `2676799` |
| #98 | docs: document integrity security controls | `0993c34` |
| #99 | fix: revalidate evidence excerpts against source (GAP B) | `5b55fe9` |
| #100 | docs: remove hard-coded test count | `27610ad` |
| #101 | docs: pre-register Golden v1 annotation protocol | `fafda76` |
| #102 | feat: add Portuguese Golden tooling | `139fc87` |
| #103 | feat: add Portuguese Golden source corpus validation | `93609e6` |
| #104 | build(deps-dev): update protobuf requirement from <7,>=5 to >=5,<8 | `5cec12b` |
| #106 | build(deps-dev): update mypy requirement from <2,>=1.17 to >=1.17,<3 | `db721d0` |
| #107 | chore(deps): bump actions/dependency-review-action from 4.9.0 to 5.0.0 | `14c9a52` |
| #108 | fix(ci): scope concurrency groups per PR/ref | `5301b21` |
| #109 | docs: report v0 and v0.1 side by side | `f705a5a` |
| #110 | fix: align Path B translation provenance with license policy | `d245e68` |
| #111 | fix(stance): Portuguese negation, dates and directional antonyms | `5b606fe` |
| #112 | docs(eval): pre-register F1.2 rule path C measurement | `b57cb44` |
| #113 | docs(eval): publish F1.2 results (rule path C v4 vs v5) | `f6f0607` |
| #114 | eval+feat: real Penal Code audit simulation and rule stance v6 | `a44f717` |
| #115 | docs(research): technology radar for Portuguese auditable verification | `3be512b` |
| #116 | docs: clarify historical and current Path C accuracy | `1b45dc9` |
| #117 | docs: clarify Golden evaluation caveat and metric glossary | `9d36588` |
| #118 | docs: clarify historical Golden review state | `1bb4c7d` |
| #119 | docs: add ADR index for architecture and evaluation decisions | `c4dc361` |
| #120 | docs: add master traceability matrix | `6cd79b9` |
| #121 | test: isolate .attractor runtime data from repository root | `4f094a1` |
| #122 | feat(evaluation): add deterministic semantic digest v1 | `8e596f5` |
| #123 | Phase 1.1 — Freeze legacy baseline predictions | `82bff0f` |
| #124 | CI reproducibility — pin GitHub Actions to Ubuntu 24.04 | `4d47424` |
| #125 | feat(1.2a): separate operation status from factual verdict | `2c01b67` |
| #126 | feat(storage): version SQLite audit schema and preserve replay history (1.2b) | `22be21d` |
| #127 | docs(adr): accept deterministic adjudication contract (ADR-009) | `3c9547e` |
| #128 | docs(provenance): map audit trail concepts to W3C PROV-O | `f4afcad` |
| #129 | refactor(1.3): remove legacy verification status authority | `2ac98ad` |
| #130 | docs: record pending architecture and governance decisions | `e91e9cb` |
| #131 | evals: add separate manifest for Golden v0.1 | `c3978ed` |
| #132 | F1.3: preserve r1-a wire responses with ResponsePolicy | `62b0cd3` |
| #133 | docs: neutral authorship and review attribution | `bfd1a9e` |
| #134 | docs: record DEC-005 for invalid r1-a inputs | `5ab8f32` |
| #135 | docs: approve DEC-005 option A | `4f7abfc` |
| #136 | feat: separate response policy from factual verdict | `d4964b0` |
| #137 | docs: align status pages to traceability master | `894fff5` |
| #138 | docs: audit public claims and evidence sources (M5) | `f40678e` |
| #139 | fix: return structured 422 for invalid r1-a requests (DEC-005) | `53d0a74` |
| #140 | docs: add legal-domain scope and citation rules | `8b26745` |
| #141 | docs: clarify Q2 modules outside verified scope | `b0821d1` |
| #143 | docs: cite ADR-009 in public-claim evidence map | `9f49ed7` |
| #144 | test: enforce verdict authority boundaries and CLI contract | `974a3c6` |
| #145 | docs: define PT-BR annotation protocol draft | `76b79d5` |
| #146 | docs: define PT-BR source registry and primary-source candidates | `35f03c6` |
| #147 | test: raise verification backend coverage gates | `da05861` |
| #148 | docs: prepare v0.4.0 and record Phase 1 gates | `e371cc1` |
| #149 | fix: close stores and enforce resource warning gate | `74d648a` |
| #150 | feat: introduce versioned Judge 2.0.0 rules contract | `07e9568` |
| #151 | docs: finalize v0.4.0 release metadata | `11108cd` |
| #152 | docs(research): add RN-001 second-layer questioning proposal | `d4d1c16` |
| #153 | feat(judge2): implement G1/G2 gates and E1-E3 admissibility | `2f660e0` |
| #154 | feat(judge2): deterministic atomic and composite rules (item 2.3) | `e92879d` |
| #156 | docs: refresh public metadata after v0.4.0 | `423938a` |
| #157 | docs: correct Golden v0.1 manifest ancestry note | `ea3cc32` |
| #158 | docs: adicionar identidade visual do AYORAI ATTRACTOR | `11929f1` |
| #159 | docs(judge2): mark item 2.3 complete and document in-process boundary | `43a2c88` |
| #160 | feat(judge2): canonical output and deterministic hashes (item 2.4) | `c7e3868` |
| #161 | feat(api): expose Judge 2.0 through r2-a on /v1/verify (item 2.5) | `18bd75e` |
| #162 | ci(api): guard OpenAPI contract with oasdiff and Schemathesis (stage B) | `4d32b9b` |
| #163 | feat(api): complete r2-a response and error contracts (item 2.5) | `3c469b8` |
| #164 | fix(judge2): canonicalize Judge 2 hashes with RFC 8785 | `ccebb54` |
| #165 | feat(eval): add deterministic derived Golden r2 migration (item 2.6) | `2b70b9f` |
| #166 | chore: merge current main into B2 API contract branch | `b5acb1d` |
| #167 | feat(judge2): canonical-result explanations and traceability (item 2.7) | `74f622b` |
| #168 | chore: merge main into item 2.7 branch after API contract merge | `7a85143` |
| #169 | fix(api): restore legacy max_agents coercion on /v1/opensearch | `46867e1` |
| #170 | release: prepare v0.5.0 (Phase 2 — Judge 2.0) | `e9eccb5` |
| #171 | docs: record v0.5.0 Zenodo DOI | `45f109e` |
| #172 | docs: sync status documents after v0.5.0 | `adb9f58` |
| #173 | docs(api): clarify legacy max_agents coercion wording after v0.5.0 | `b0082ce` |
| #174 | docs(eval): pre-register PT-BR RGC benchmark design (proposed) | `d962a2e` |
| #175 | docs(legal): full Apache-2.0 text, authorship NOTICE and prior-IP record | `7c596b2` |
| #176 | docs: record DEC-002 source licensing and provenance policy | `c25264b` |
| #177 | data(ptbr): byte-exact capture and provenance of the RGC official sources | `baa0eaf` |
| #178 | data(ptbr): deterministic derived text of the RGC sources | `33061c9` |
| #179 | eval(ptbr): executor determinístico do benchmark RGC [PROPOSTO] | `c267d00` |
| #180 | docs(rgc): synchronize benchmark status and gates | `1d85903` |
| #181 | docs(rgc): record pending label and authorship decisions | `484cfc7` |
| #183 | docs(institutional): add technical dossier draft | `2d6503f` |
| #184 | docs(institutional): add university research proposal draft | `f1e574c` |
| #185 | docs(institutional): add 12-month research work plan draft | `0fb1b08` |
| #186 | docs(eval): rename RGC collection heading | `0b67e15` |
| #189 | build(deps-dev): update transformers requirement from <5,>=4.55 to >=4.55,<6 | `2fc8d31` |
| #190 | build(deps): bump actions/upload-artifact from 7.0.1 to 7.0.2 | `4ce728f` |
| #192 | fix(judge2): adjudicate r2-a evidence with canonical_url (#182) | `61ad997` |
| #193 | docs(rgc): align protocol with approved Judge 2.0 decisions | `e60f91a` |
| #194 | docs(rgc): record approved DEC-007 to DEC-009 | `890d138` |
| #195 | eval(ptbr): report Judge decision states in the RGC runner (DEC-009) | `b982574` |
| #196 | ci: bump all CodeQL actions to v4.38.3 together | `ab6b810` |
| #197 | docs: sync RGC benchmark status and evidence | `5155776` |
| #198 | docs(rgc): clarify compound-claim limitation | `140e92d` |
| #199 | docs(decisions): add pending DEC-010 for RGC compound claims | `5f9bcd4` |
| #200 | docs(progress): update RGC status for 2026-10-16 | `1fe596c` |
| #201 | ci(dependabot): group CodeQL action updates | `a922d41` |
| #203 | eval(ptbr): annotated atoms for compound claims in the RGC runner (DEC-010 A) | `19ccc25` |
| #204 | docs(decisions): approve DEC-010 for compound RGC claims | `2cabc17` |
| #205 | docs(protocol): add Amendment 3 for compound claims | `0ea36d6` |
| #206 | docs(decisions): propose DEC-011 annotation-guide fixes from the RGC pilot | `a57dbe7` |
| #207 | docs(decisions): DEC-011 records choice A for Part 2 | `2f1ec89` |
| #208 | docs(status): record DEC-010 approval and completed exploratory pilot | `4bb47d6` |
| #209 | docs(eval): propose report for exploratory RGC pilot | `e0e1551` |
| #210 | docs(institutional): update RGC pilot status and next steps | `be9fa95` |
| #211 | docs: add external-reader glossary draft | `c4c5dae` |
| #212 | ci(api): fixed Schemathesis seed and saved reports | `8651575` |
| #213 | build: make reproduce — re-run the CI evidence with one command | `7546cb9` |
| #214 | test: cover and label the six unused experimental modules | `d8b13b9` |
| #215 | build: ship py.typed and gate the RGC runner with strict mypy | `d68439f` |
| #216 | style: apply ruff format (79 files, AST-identical) and enforce it in CI | `2a4d5ac` |
| #217 | fix(audit): reject duplicate trace IDs and document integrity limits | `50610f0` |
| #218 | fix(api): enforce configurable request body size limit | `96cc965` |
| #219 | feat(api): add optional API key authentication | `1344acb` |
| #220 | docs(adr): propose verifiable audit log | `fe91534` |
| #221 | feat(api): add request IDs and privacy-safe access logs | `02413a6` |
| #222 | fix(docker): harden container runtime defaults | `579fd83` |
| #223 | test(api): verify body limit with real Uvicorn | `decb157` |
| #224 | fix(judge2): ship Judge rules in the package so pip installs can adjudicate | `29496fd` |
| #225 | docs(adr): record owner decisions 1-4 for the verifiable audit log (DEC-012) | `20dcdb8` |
| #226 | test(docker): verify API key authentication in container | `09c5699` |
| #227 | docs: formalize approved DEC-011 annotation rules | `82ee377` |
| #228 | docs: reconcile RGC status after DEC-011 approval | `dffc9f7` |
| #229 | docs: reconcile RGC protocol and prepare isolated pilot worksheet | `0f80f38` |
| #230 | docs: sync status pages with approved DEC-011 and merged PRs | `4a5079b` |
| #231 | docs(decisions): add decision index and update stale implementation states | `7f72bbe` |
| #232 | eval(ptbr): report rectified cases as a separate stratum (Amendment 4) | `b7a076f` |
| #233 | tools(eval): offline mechanical checker for the pilot-02 worksheet | `ab13f73` |
| #234 | docs(changelog): record changes merged since v0.5.0 under Unreleased | `b44d6ff` |
| #236 | feat(auditlog): ADR-010 phase 1 core library (Merkle proofs, salted commitments) | `e50d2b9` |
| #241 | docs(eval): propose RGC statistical-design clarifications before freeze | `d8411d9` |
| #242 | docs(audit): technical audit of changes since v0.5.0 | `919ba7b` |
| #243 | docs: add AGENTS.md governance and identity rules | `e51d6a6` |
| #244 | docs: correct governance scope and pilot rationale (PR #243 follow-up) | `13dc9fd` |
| #245 | docs(agents): align authorship rule with maintainer-responsible practice | `86c158b` |
| #246 | docs(governance): disclose supervised automated assistance | `d4d76e9` |
| #247 | docs(readme): align public status with verified evidence | `cc0e7ac` |
| #248 | docs(scope): mark experimental modules outside verified core | `03b8603` |
| #249 | docs(status): establish a single current-status source | `b585bc7` |
| #251 | docs(status): keep canonical status page current | `a2c08e5` |
| #252 | security(api): fail closed when authentication is not configured | `7d8c27d` |
| #253 | ci(schemathesis): preserve reproducible contract-test evidence | `d022865` |
| #254 | docs(governance): refresh DEC-012 merge status | `86e27a2` |
| #255 | docs(status): reconcile open PRs and decision gates | `d174648` |
| #256 | fix(api): enforce fail-closed startup under Uvicorn | `e6c4e01` |
| #257 | docs(agents): clarify current runtime behavior | `6fbb58a` |
| #258 | docs(governance): record DEC-013 agent execution authorization | `22fece0` |
| #259 | ci(schemathesis): apply legacy max_agents exclusion to /v1/audit (fixes #250) | `ec8b71b` |
| #260 | fix(api): emit structured access records under Uvicorn | `2da10d5` |
| #261 | test(docs): fail on broken relative links and anchors | `3587248` |
| #262 | docs: establish technical manual governance and style | `3c1ba4f` |
| #263 | docs: add technical manual overview | `418a82f` |
| #264 | docs: document service and library architecture | `a120545` |
| #266 | docs: reorganize ATTRACTOR documentation for audit-focused clarity | `ae44c23` |
| #267 | docs: add public technical document v1.1 and audit report | `f9ece75` |
| #268 | docs: link public technical PDF in documentation navigation | `71e682c` |
| #270 | docs: corrigir corte dos rótulos no diagrama do fluxo de verificação | `6f3588b` |
| #271 | docs: document deterministic Judge rules and traceability | `3e68b70` |
| #273 | docs: review RGC PT-BR benchmark methodology | `5719db4` |
| #274 | fix: enforce RGC baseline B from public development partition | `c639d0f` |
| #275 | docs: clarify pilot-only RULE_GAP annotation marker | `9610d24` |
| #278 | fix(eval): honor requested Golden suite in H1 runner | `a607779` |
| #279 | docs(eval): clarify RGC statistics contract | `7a4a268` |
| #280 | docs(status): refresh RGC execution snapshot | `2fd65ca` |
| #281 | docs(eval): clarify RGC bootstrap contract and pending amendment | `f618306` |
| #284 | fix(governance): restore RGC preregistration audit trail | `2ed5aca` |
| #286 | docs(governance): record maintainer authorization DEC-016 | `d958474` |
| #288 | docs(eval): incorporate RGC baseline B amendment 6 | `5a587ec` |
| #289 | docs(api): record frozen r1-a null-body contract history | `d2ac642` |
| #291 | test(api): clarify frozen r1-a null-body contract drift | `e52af83` |
| #292 | docs(status): refresh RGC test and governance snapshot | `1b8a08a` |
| #293 | build(deps): update CodeQL action pins to v4.39.0 | `76de473` |
| #294 | fix(eval): mark report manifests from non-CI runs | `8664286` |
| #295 | docs(status): move historical snapshots to history | `a706de0` |
| #296 | docs(eval): reconcile RGC baseline status after amendment 6 | `32c4f9e` |
| #297 | docs(eval): link missing-versus-invalid contract to DEC-017 | `62d01df` |
| #299 | docs(eval): record pending confirmatory H1 scope | `8e833b3` |
| #300 | docs(eval): record pending article-cluster bootstrap decision | `a3b0496` |
| #301 | docs(eval): record pending annotator agreement criterion | `680a8ea` |
| #302 | docs(audit): record known squash-message deviations | `c390215` |
| #303 | docs(eval): prepare human-only pilot 02 workflow | `f305790` |
| #304 | docs(eval): append dated status for RGC methodology findings | `e313326` |
| #305 | docs(manual): add chapter 04 on HTTP API contracts | `64461fd` |
| #306 | docs(manual): add chapter 05 on operations | `42b71a2` |
| #308 | docs(manual): add chapter 06 on security boundaries | `0747cd6` |
| #309 | docs(manual): add chapter 07 on reproducibility | `220e0f3` |
| #311 | test(providers): cover unknown provider registry path | `20376f5` |
| #314 | test(agents): cover research provider failure paths | `9bd8385` |
| #316 | docs(decisions): normalize DEC-016 and DEC-017 headings | `2ca7cc5` |
| #320 | docs(rgc): clarify current preregistration reading | `2f990b6` |
| #323 | eval(rgc): approve DEC-017 invalid-prediction handling | `8db1a56` |
| #326 | eval(rgc): scope confirmatory H1 to hidden partition | `22b3a0d` |
| #331 | fix(governance): restore DEC-018 as pending and revert unapproved partition scope | `00e39c1` |
| #333 | fix(governance): restore DEC-017 as pending | `568dfe0` |
| #335 | eval(rgc): ratify DEC-017 invalid-prediction handling | `ecd9f7c` |
| #337 | eval(rgc): restore explicit DEC-017 option A approval | `97af24c` |
| #339 | test(api): record controlled null-body dependency reproduction | `ed90cf6` |
| #342 | eval(rgc): restore approved DEC-018 hidden-only H1 | `e03d69b` |
| #345 | docs(manual): add chapter 08 on evaluation | `0d1d649` |
| #349 | eval(rgc): implement approved DEC-019 article-cluster bootstrap | `846d5bf` |
| #351 | eval(rgc): implement approved DEC-020 annotator agreement | `a059f20` |
| #352 | docs(rgc): update methodology review after approved decisions | `34c53b2` |
| #353 | quality: raise low-module coverage and extend strict mypy | `75c42e5` |
| #354 | security: remove remaining Bandit comment parser warnings | `720c082` |
| #355 | docs(manual): add chapter 09 audit and traceability | `1579041` |
| #356 | docs(manual): add chapter 10 governance and decisions | `52949d5` |
| #357 | docs(release): update Unreleased and draft v0.6.0 notes | `5c205f8` |
| #358 | docs(audit): record branch cleanup scope and limitation | `7cf0d9e` |
| #359 | docs(status): refresh main snapshot and human gates | `210af8f` |
| #360 | docs(audit): correct branch cleanup candidate inventory | `f24470d` |
| #361 | docs(eval): reconcile approved DEC-017–020 amendments | `97191b8` |
| #362 | test(docs): guard approved amendment consistency | `0f06995` |
| #363 | eval(rgc): bump runner report version to 0.5.0 | `66e8bf6` |
| #365 | test(api): extend null-body compatibility version sweep | `dc91b0a` |
| #366 | docs(rgc): annotate superseded DEC-017/018 text | `6bc0853` |
| #369 | test(rgc): prevent approved amendment contradictions | `1e77df7` |
| #370 | docs(rgc): clarify approved amendment history | `7fc9ae9` |
| #373 | security: document rationale for nosec suppressions | `fc12c38` |
| #374 | docs(status): reconcile final evidence and v0.6.0 draft | `a269d5f` |
| #375 | test(rgc): consolidate approved amendment guards | `daf9ce3` |
| #376 | docs(audit): record final process deviations | `c9994dd` |
| #377 | docs(status): finalize closeout evidence and v0.6.0 draft | `bfadec8` |
| #378 | feat(eval): block RGC runs until protocol freeze is attested | `400c5c5` |
| #379 | fix(eval): bind RGC freeze to exact runner specification and code | `ec80395` |
| #380 | fix(eval): require declared source provenance in pilot checker | `eade15e` |
| #381 | docs(status): record RGC freeze and provenance gates | `9045549` |
| #382 | feat(eval): require approved dual-annotation evidence for RGC runs | `44291a2` |
| #383 | ci: run RGC design simulation on relevant changes | `ea4e7de` |
| #384 | test(rgc): cover synthetic design simulation invariants | `5ad402a` |
| #385 | fix(eval): advance RGC runner version to 0.6.0 | `970af6d` |
| #386 | docs(status): reconcile RGC integrity gates and runner 0.6.0 | `5e8a6e6` |
| #387 | docs(status): record annotator independence verification limit | `f4b593f` |
| #388 | docs(manual): align chapter index with current status | `620e39f` |
| #389 | docs(status): record manual index reconciliation | `2708ce5` |
| #390 | test(audit): cover report findings and failure severity | `a1fe33e` |
| #391 | test(extraction): cover provenance and adapter contracts | `bf49dba` |
| #393 | fix(extraction): validate NLI payloads and source offsets | `a44d056` |
| #394 | docs(status): record extraction fixes and current PR state | `f94e86d` |
| #395 | docs(status): clarify snapshot timestamp and follow-up merge | `bd99f4b` |
| #396 | docs(status): record PR #395 merge and main reference | `f7277d3` |
| #397 | docs(status): record PR #396 merge and checks | `33393f8` |
| #398 | fix(rgc): validate gold label JSONL strictly | `6415919` |
| #399 | chore(rgc): align runner version and consolidate process updates | `3f12d54` |
| #400 | docs(v0.6.0): audit compatibility, documentation states, and DOI semantics | `27cc948` |
| #401 | docs(v0.6.0): precise auth history and document-specific audit reasons | `3642e43` |
| #402 | release: prepare v0.6.0 | `6fcdb7d` |
| #405 | docs: register published v0.6.0 | `b52035f` |
| #406 | docs: record v0.6.0 artifact provenance | `21330a0` |
| #407 | docs: refresh RGC continuity and current status | `5ce63a9` |
| #408 | docs: record DEC-016 process deviations | `4755f94` |
| #409 | docs: record main CI and release status | `d45e48d` |
| #410 | test: expand coverage for extraction audit and orchestration | `4f3c0ce` |
| #411 | docs: record final coverage and CI snapshot | `2dc089f` |
| #412 | ci: add manual merged-branch cleanup workflow | `e7bce5c` |
| #418 | build(deps): bump the codeql-action group with 3 updates | `c1605e7` |
| #419 | build(deps): bump actions/setup-python from 7.0.0 to 7.1.0 | `e4471b8` |
| #439 | docs: adiciona link para o site oficial no README | `0b2d92f` |
| #442 | feat(api): add bounded authentication rate limiting | `7bb9381` |
| #443 | fix(audit): serialize shared SQLite store access | `1a2afff` |
| #445 | fix(api): isolate rate limiters and document 429/proxy trust | `22e63fb` |
| #446 | test(verification): verify offline pipeline with sockets blocked | `478ae8d` |
| #448 | chore: transplante do Grupo 1 (sem #417; #428, #429, #430, #416, #440, #441, #413, #414, #426, #438, #423) | `036f2f7` |
| #449 | ci(build): make distribution builds reproducible and attempt-scoped | `981cd39` |
| #450 | docs(readme): add Docker and curl verification demo | `96b4f3b` |
| #452 | fix(rgc): bind annotation IDs and reject hidden RULE_GAP | `1e5b56f` |
| #454 | fix(rgc): validate cluster IDs against cited articles | `d7f43f9` |
| #457 | docs(rgc): reapply only #417 delta after #454 | `36c085d` |
| #459 | feat(diagnostics): reapply failure stage on current main | `26eaa8b` |
| #460 | docs(verification): clarify original Unicode excerpt offsets | `d9c1fa2` |
| #461 | docs(contributing): add public claims policy | `8c45231` |
| #462 | docs(benchmarks): document dataset provenance and label mappings | `21ab0c4` |
| #463 | feat(benchmarks): add local international evaluation harness | `a6e6545` |
| #464 | chore(benchmarks): pin LLM-AggreFact test shard (#?) | `5f79290` |
| #465 | feat(benchmarks): add gated DEV throughput pilot (#465) | `91977dc` |
| #466 | docs(benchmarks): propose Phase 1b sharded international evaluation | `a04c865` |
| #467 | feat(benchmarks): implement Phase 1b DEV-only sharded pipeline | `0b83fd3` |
| #468 | docs(rgc): record DEC-021..DEC-023 statistical amendments | `b358b4d` |
| #469 | docs(benchmarks): correct download-artifact v7 pin | `9704717` |
| #470 | docs(status): update benchmark and Phase 1b status | `9712f03` |
| #471 | docs(benchmarks): register LLM-AggreFact TEST RuleStance baseline report | `0c21656` |
| #472 | feat(benchmarks): add DEV calibration and metrics module | `e1d7742` |
| #473 | docs(benchmarks): preregister calibration v2 protocol | `b8d98d7` |
| #474 | feat(benchmarks): calibration v2 — deterministic splits and probabilistic metrics | `1c7f734` |
| #475 | feat(benchmarks): calibration v2 — Venn-Abers (IVAP) with cross-fitting and Mondrian | `90854ff` |
| #476 | feat(benchmarks): calibration v2 — selective Learn then Test certification | `3a7ea75` |
| #477 | docs(calibration): preregister single-model selection for V2 certification | `d7ebf5b` |
| #478 | fix(api): use server-generated request correlation IDs | `89ad2c9` |
| #479 | feat(benchmarks): integrate Calibration V2 in DEV aggregator | `1bce4f2` |
| #480 | feat(benchmarks): add maintainer-gated full DEV workflow | `34b7ccd` |
| #481 | fix(benchmarks): make Calibration V2 aggregation runnable and add re-aggregation path | `c3946ae` |
| #482 | docs(benchmarks): record first DEV Calibration V2 result | `5cf34d7` |
| #483 | docs(readme): present Calibration V2 DEV results | `140c4d9` |
| #484 | chore(release): prepare v0.7.0 | `43bbe8e` |
| #485 | docs(release): record v0.7.0 version DOI | `3e124a5` |
| #486 | docs(project): align public documentation with v0.7.0 | `e643caa` |
| #487 | site: align public website with v0.7.0 and current evidence | `8af5012` |
| #488 | feat(calibration): amendment 2 — skip ineligible thresholds in Learn then Test | `caa912c` |
| #489 | docs(benchmarks): add v0.8 accuracy roadmap | `f8895ca` |
| #490 | docs(benchmarks): add technology radar and contamination gate | `b64ebe2` |
| #491 | docs(rgc): document component-level statistical decisions | `f8d4648` |
| #492 | docs(benchmarks): record exploratory Amendment 2 results and LTT power analysis | `798d7b2` |
| #493 | docs(decisions): record DEC-024 — option B (calibration and fixed-rule combination only) | `0f8f0d1` |
| #494 | ci: pin ruff to 0.17.4 | `7a66892` |
| #495 | docs(benchmarks): preregister E3 ensemble v0.8 | `49b4ea9` |
| #496 | feat(benchmarks): A1 — encrypted DEV score cache and cache experiment workflow | `22adc02` |
| #497 | feat(benchmarks): E3 fixed-rule ensemble on the DEV score cache | `42d63e1` |
| #499 | docs(benchmarks): add A4 contamination ledger v0.8 | `dfce685` |
| #501 | docs(benchmarks): maintainer approval of the E3 preregistration for exploratory DEV run | `ba65753` |
| #502 | ci: retry transient pinned release downloads | `2523588` |
| #503 | docs(benchmarks): publish exploratory E3 DEV-A results | `90d0ec3` |
| #508 | feat(benchmarks): rebuild document ids for the DEV score cache (cache v2) | `22c5808` |
| #511 | feat(api): POST /v1/check — verify claims or an AI answer against documents | `ed533aa` |
| #513 | docs(governance): allow merges only with individual maintainer authorization | `539b985` |
| #515 | fix(api): bind field-check traces to complete document identity | `6b46b88` |
| #516 | fix(check): bind trace identity to page boundaries | `f949e53` |
| #518 | build(deps): bump the codeql-action group with 3 updates | `bd3d262` |
| #520 | build(deps): bump actions/download-artifact from 7.0.0 to 8.0.2 | `ec7b824` |
| #525 | ci: validate benchmark and artifact dependency pins | `b64e56d` |
| #526 | docs(api): document /v1/fields trace identity v2 | `b26d358` |
| #532 | feat(rgc): implement deterministic connected article components | `0cbca11` |
| #533 | security(ci): enforce strict dependency audit gates | `b650d9e` |
| #536 | security(deps): audit a modern NLI environment without touching the historical one | `0ec370b` |
| #537 | chore(release): prepare v0.8.0 | `9833d24` |
| #538 | security(ci): disable persisted checkout credentials across workflows | `85c28b4` |
| #540 | security(ci): grant write permissions per job, never per workflow | `ffe4a4e` |
| #541 | docs(changelog): record checkout and permission hardening in v0.8.0 | `92ea5eb` |
| #542 | docs: synchronize public project status with v0.8.0 | `8a8ddc5` |
| #543 | site: synchronize official pages with v0.8.0 | `346072a` |
| #544 | docs(status): remove stale v0.7.0 claims after the v0.8.0 release | `d10c40b` |
| #545 | fix(fields): accept only plain ASCII digits (field-check-3) | `228a0f3` |
| #546 | fix(fields): a minus sign before a number or amount belongs to it (field-check-4) | `db66296` |
| #547 | feat(eval): passage-relation protocol and harness for /v1/check contradictions | `8feb72b` |
| #548 | docs(decisions): DEC-027 RGC statistical reconciliation | `5fea78a` |
| #549 | feat(rgc): RGC-PRNG-1 and type-7 percentile for every RGC bootstrap (E2) | `512938e` |
| #550 | feat(rgc): one canonical article ID grammar for citations, bundles and components (E1) | `4c48a4f` |
| #551 | feat(rgc): add pre-annotation component resolution gate (E4/D7) | `da864db` |
| #552 | feat(rgc): H1 by component sign-flip and component CI in the runner (Emenda 11) | `6f4d413` |
| #555 | fix: concurrency, integrity and credential-safety fixes; /v1/check CPU cost | `85d6c2b` |
| #556 | Integração 1/7: testes do Judge 2.0, imagem Docker fixada, cenários E2E, correções de documentação, CLI e limite de concorrência | `dae9c5c` |
| #561 | Integração 2/7: respostas limitadas, sem compressão e com prazo total nos providers HTTP | `479b785` |
| #562 | Integração 3/7: pisos de segurança das dependências e imagem Docker com lock por hash | `049abfe` |
| #563 | Integração 4/7: limite de concorrência opcional compartilhado entre workers do mesmo host | `ea724e5` |
| #564 | Integração 5/7: trilha de auditoria com dono, r2-v3, metadados, backup e HMAC | `fe82d76` |
| #565 | Integração 6/7: detector por regras v8 (negação sentencial e base de comparação) e erros conhecidos fixados | `36bcbe0` |
| #566 | Integração 7/7: documentação de /v1/check, /v1/fields, dono dos rastros, backup e novas variáveis | `297fe38` |
| #567 | chore(deps): Dependabot sem os pins históricos do benchmark e sem novas linhas de Python na imagem | `a9d7a5a` |
| #568 | ci(security): varredura da imagem com Grype e proveniência SLSA assinada das distribuições | `87ed97d` |
| #569 | build(deps-dev): bump ruff from 0.17.4 to 0.17.5 | `267a29e` |
| #570 | fix(stance): negação restrita às frases da afirmação e negação relatada neutra (detector v9) | `fa36a4b` |
| #572 | docs(status): refresh engineering status for 2026-11-16 | `630b6d1` |
| #574 | docs(security): document audit integrity and admission controls | `345e94f` |
| #575 | fix(audit): enforce HMAC across replay versions | `751fd4f` |
| #578 | docs(status): refresh engineering status for 2026-11-17 | `73bf91c` |
| #582 | build(deps): bump transformers from 5.22.2 to 5.23.0 | `c80ade0` |
| #585 | fix(stance): afirmações hipotéticas e valores-limite não confirmam a afirmação (detector v10) | `d2e3d5d` |
| #586 | feat(audit): retenção automática dos rastros e volume persistente no Compose | `e4ef3c1` |
| #587 | feat(api): POST /v2/audit — busca e adjudicação ADR-002 ponta a ponta | `18528a9` |
| #588 | docs(release): CHANGELOG consolidado desde a 0.8.0 e guia de limite de requisições entre réplicas | `5c757ac` |
| #589 | fix(check): todo documento relacionado chega à adjudicação (document-check-3) — P0 | `1abe7ea` |

## 5. Branches (105 remotas)

- 24 com PR aberta; 3 com PR mesclada e branch ainda presente; 54 com PR fechada; 22 sem nenhuma PR (9 sem commits fora da `main`; 13 com commits exclusivos); `main`; `gh-pages`.
- **Com trabalho nunca submetido e que exige decisão:** `eval/rgc-pilot` (altera dados do piloto RGC, `SOURCES-REGISTRY.json` e capturas em `evals/ptbr/sources/`, artefatos protegidos; conteúdo não aberto nesta auditoria); `eval/dec-020-kappa-criteria-2026-10-21` e `docs/rgc-amendments-consistency-2026-10-21` (protocolo e pré-registro); `feat/rgc-annotation-approval-gate` (runner).
- Nenhuma branch foi apagada. Candidatas à remoção, sujeitas à decisão do mantenedor: as 3 com PR mesclada, as 9 sem commits próprios e as 54 com PR fechada cuja análise acima mostra conteúdo resolvido, substituído ou obsoleto.

## 6. Pendências reais encontradas nesta reconciliação

1. **Registro de decisões:** DEC-017..020, DEC-023 e DEC-027 constam como "Estado vigente: Aprovada" só em `docs/DECISIONS-PENDING.md`, não em `docs/DECISIONS-APPROVED.md` (relacionado à #239, fechada). Os dois arquivos são protegidos: decisão do mantenedor.
2. **Pins históricos com avisos de segurança** (`requirements-benchmark-pilot.txt`; Dependabot #519–#524, #558, #559): decisão do mantenedor (P3-1).
