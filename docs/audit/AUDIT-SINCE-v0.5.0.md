# Auditoria técnica — AYORAI ATTRACTOR desde a v0.5.0

| Campo | Valor |
|---|---|
| Versão de referência | v0.5.0, publicada em 2026-10-13 (tag no commit `e9eccb50e4904b8f33004a414a5666477378c67a`; DOI 10.5281/zenodo.23344005) |
| Estado auditado | `main` em `e50d2b9bc623d1ad0dd95302e4602653e3dcbac2` (2026-10-17) |
| Intervalo | 63 commits na `main` desde a tag; 61 PRs mescladas até #245, com lacunas na numeração (contagem derivada do compare de commits e dos merges registrados) |
| Solicitante | Anderson Leon Ayora (mantenedor) |
| Natureza | Documento de engenharia. Não altera código, decisões, ADRs, regras, Golden, manifestos ou hashes. |

## 0. Método e regra de evidência

Nenhum item é classificado como implementado sem **código na `main`**, **teste que o exercita** e **execução registrada**. Fontes consultadas:

1. Compare da tag v0.5.0 (`e9eccb5`) até a `main` auditada (`e50d2b9`): 63 commits. A afirmação histórica de que os 58 commits até `ab13f73` tinham um único pai não é automaticamente transferida para os commits posteriores; a estrutura de pais do intervalo atualizado não foi revalidada localmente nesta sessão.
2. API REST do GitHub: PRs mescladas e abertas, check-runs, ruleset `Protecao-main-ATTRACTOR`, releases e comentários.
3. Última execução local declarada nesta matriz: **658 testes aprovados em `ab13f737`** (Python 3.13.16, `pytest -q`). Esse resultado é histórico e não prova a suíte no SHA `e50d2b9`; não houve execução local nesta sessão.
4. Check-runs do SHA `e50d2b9`: os seis checks obrigatórios (test 3.11/3.12/3.13, golden-regression, judge-regression, security) foram conferidos no GitHub; o job `analyze` ainda estava em andamento na consulta inicial e não é um check obrigatório de merge.
5. Leitura direta dos arquivos citados, com caminho e linha.

### Legenda

| Classe | Significado |
|---|---|
| **IMPLEMENTADO** | Na `main`, com teste dedicado e CI verde no SHA auditado. |
| **IMPLEMENTADO — LIMITADO** | Na `main` e testado, mas com limitação explícita que impede afirmar a propriedade completa. |
| **EM PR** | Código ou texto em PR aberta; não está na `main`. |
| **PROPOSTO** | Documentado como proposta, sem implementação. |
| **PENDENTE** | Depende de decisão do mantenedor, de trabalho humano ou de validação ainda não realizada. |

## 1. Resumo do estado

| Área | Estado | Síntese |
|---|---|---|
| Judge 2.0 e contrato `r2-a` | IMPLEMENTADO | Sem mudança de regras desde a v0.5.0. Uma correção de entrada (`canonical_url`, #192) e o empacotamento das regras (#224). `rules_sha256` inalterado. |
| Autenticação por API key | IMPLEMENTADO — LIMITADO | HMAC-SHA-256 com pepper, *fail-closed* na configuração. **Desligada por padrão na aplicação**; ligada por padrão no Compose. |
| Request ID e log de acesso | IMPLEMENTADO | Sem corpo, afirmações, trechos, *query string* ou credenciais no registro. |
| Limite de tamanho do corpo HTTP | IMPLEMENTADO | 2 MiB por padrão; testado com Uvicorn real, com e sem `Content-Length`. |
| Contêiner Docker | IMPLEMENTADO — LIMITADO | Usuário não root, `HEALTHCHECK`, porta só em `127.0.0.1`, smoke test autenticado. **Imagem base sem digest** (DEC-001 pendente). |
| Registro de auditoria verificável (ADR-010) | PROPOSTO / EM PR | O armazenamento atual **não** é à prova de adulteração. Decisões 1–4 em PR (#225); biblioteca da fase 1 em PR (#236). Nenhum campo de auditoria na API. |
| Benchmark RGC PT-BR | PENDENTE | Fontes capturadas, executor proposto, emendas 1–4. **Protocolo não congelado. Nenhum resultado.** |
| Reprodutibilidade e CI | IMPLEMENTADO | `make reproduce`, seed fixa no Schemathesis, `ruff format` obrigatório, `mypy --strict` no executor, `py.typed`. |
| Cadeia de suprimentos | PENDENTE | Sem `uv.lock`, sem digest de imagem, sem SBOM, sem assinatura de release (DEC-001 pendente). |
| Governança e documentação | IMPLEMENTADO — LIMITADO | Status reconciliado (#230, #231, #234). Comentários antes rotulados como revisão independente foram reidentificados como revisões automatizadas publicadas pelo mantenedor; a revisão humana independente das PRs desde a v0.5.0 continua pendente (F-01). |

## 2. Matriz de auditoria

### 2.1 Judge determinístico e contrato da API

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Evidências `r2-a` com `canonical_url` são adjudicadas, sem `SCHEMA_VIOLATION` | IMPLEMENTADO | PR #192 (issue #182); testes de regressão na PR | — |
| Regras do Judge distribuídas no pacote | IMPLEMENTADO | PR #224; `src/ayorai_attractor/verification/judge2/__init__.py:26`; `tests/verification/test_judge2_packaged_rules.py` (4 testes: identidade de bytes, `rules_sha256` canônico, *checkout* × instalado) | Duas cópias byte a byte idênticas; o teste falha se divergirem |
| Regras, Golden e hashes congelados inalterados desde a v0.5.0 | IMPLEMENTADO | `golden-regression`, `judge-regression` e `golden-smoke` verdes em `ab13f73` | — |
| Remoção de `ResponseStatus`, `verification`, `confidence` e do caminho `r1-a` | PENDENTE | Adiada para v0.6.0 pela DEC-008 (release) | Ainda presentes; nada removido |

### 2.2 API, autenticação e privacidade

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Autenticação opcional por API key | IMPLEMENTADO — LIMITADO | PR #219; `src/ayorai_attractor/api/auth.py` (`APIKeyAuthMiddleware`, linha 66); `tests/test_api_auth.py` (8 testes) | Padrão da aplicação: `ATTRACTOR_AUTH_MODE=off` (`auth.py:24`). Nenhum mecanismo impede subir uma instância exposta sem autenticação. Sem escopo, expiração, revogação individual nem limitação de requisições. |
| Autenticação dentro do contêiner | IMPLEMENTADO | PR #226; `.github/workflows/docker.yml`: `/health` público, 401 sem chave e com chave inválida, 200 com chave válida | Credenciais efêmeras geradas no CI |
| `X-Request-ID` e log de acesso JSON | IMPLEMENTADO | PR #221; `src/ayorai_attractor/api/request_context.py:14` (padrão `[A-Za-z0-9-]{1,64}`); `tests/test_api_request_context.py` (5 testes) | Os testes cobrem campos conhecidos. Não há verificação formal de que nenhum campo futuro vaze dados. |
| Limite de corpo HTTP (413) | IMPLEMENTADO | PRs #218 e #223; `src/ayorai_attractor/api/app.py:90`; `tests/test_api.py:200–223`; `tests/test_api_uvicorn_body_limit.py` | — |
| Contrato OpenAPI | IMPLEMENTADO | Workflows `api-contract.yml` e `schemathesis-all.yml`; seed fixa desde a PR #212 | A matriz anterior relatou uma falha não reproduzida. Os runs consultados dos SHAs documentados para #234 e #245 terminaram com sucesso; o run falho exato e seu caso falsificador não foram localizados. Ver F-06 e issue #250. |

### 2.3 Distribuição e contêiner

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Usuário não root, `HEALTHCHECK`, porta em loopback | IMPLEMENTADO | PR #222; `docker/Dockerfile:16,20`; `docker-compose.yml:9`; smoke test em `docker.yml` | O `HEALTHCHECK` só prova que `/health` responde |
| Imagem base imutável | PENDENTE | `docker/Dockerfile:1` usa a tag móvel `python:3.12-slim` | DEC-001 pendente |
| Dependências travadas | PENDENTE | Não há `uv.lock` nem arquivo de *hashes* | DEC-001 pendente |

### 2.4 Registro de auditoria

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Rejeição de `trace_id` duplicado | IMPLEMENTADO — LIMITADO | PR #217; `src/ayorai_attractor/audit_store.py:29,220` (`DuplicateAuditTraceError`); `tests/test_audit_store.py` (8 testes) | **Não** é à prova de adulteração: quem tem acesso ao banco altera linha e digest juntos (limite documentado na própria PR e na ADR-010, R1) |
| Persistência dos vereditos de `/v1/verify` | PENDENTE | ADR-010, R2 | Nada é gravado no servidor |
| ADR-010 (log Merkle C2SP) | PROPOSTO / IMPLEMENTADO — LIMITADO | PR #220 mantém o desenho proposto; DEC-012 foi registrada e mesclada na #225; a biblioteca pura da fase 1 foi mesclada na #236 | Sem persistência, API de gravação, checkpoints assinados ou implantação; o log verificável não está implementado como serviço |
| Fase 1: hashing RFC 6962, provas e compromissos com sal | IMPLEMENTADO — LIMITADO | PR #236 mesclada; vetores e testes em `tests/auditlog/`; checks obrigatórios verdes no SHA revisado antes do merge | Biblioteca pura. Não constitui log implantado. |
| Fases 2–4 (checkpoints assinados, gravação, testemunhas, carimbo do tempo) | PENDENTE | ADR-010, perguntas 5–7 abertas | — |

### 2.5 Benchmark RGC em português

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Política de fontes (DEC-002) | IMPLEMENTADO | PR #176; `docs/DECISIONS-APPROVED.md` | Não é parecer jurídico |
| Captura byte a byte e texto derivado da Resolução Anatel 765/2023 e de duas retificações | IMPLEMENTADO | PRs #177 e #178; `evals/ptbr/sources/`; `evals/ptbr/SOURCES-REGISTRY.json`; `tests/test_source_artifacts.py`, `test_source_derived_text.py`, `test_sources_registry.py` | A captura não interpreta vigência |
| Pré-registro | PROPOSTO | PR #174; `docs/eval/PREREGISTRATION-RGC-v1.md`, marcado **[PROPOSTO]** | Ver a proposta estatística (PR #241) |
| Protocolo com Emendas 1–4 | IMPLEMENTADO como documento; **não congelado** | `docs/eval/PROTOCOL-GOLDEN-V1.md`; PRs #193, #205 e #227 | O congelamento exige registro explícito do mantenedor |
| Executor `rgc-eval/0.2.0` (abstenção, átomos) | IMPLEMENTADO — LIMITADO | PRs #179, #195 e #203; `evals/ptbr/rgc_eval.py:52`; `tests/test_rgc_eval_runner.py` (23 testes, só fixtures sintéticas) | Marcado [PROPOSTO]; só validado com dados sintéticos |
| Estrato `rectified` (Emenda 4) | EM PR | PR #232 (`rgc-eval/0.3.0`) | Política para ausência do campo depende do mantenedor |
| Verificador offline da ficha do piloto 2 | IMPLEMENTADO | PR #233; `scripts/check_pilot_worksheet.py`; `tests/test_check_pilot_worksheet.py` (11 testes) | Só regras mecânicas; não avalia rótulos |
| Piloto exploratório 01 | Concluído e descartado | `docs/eval/PILOT-RGC-01-REPORT.md` | Casos redigidos por IA; anotador único; sistema não executado |
| Segundo piloto humano | PENDENTE | Ficha em branco: `docs/eval/PILOT-RGC-02-WORKSHEET.md` | Trabalho humano, sem IA |
| Golden v1, segunda anotação, conjunto oculto, execução única e relatório | PENDENTE | — | **Não existe resultado de benchmark em português** |

### 2.6 Reprodutibilidade, qualidade e CI

| Item | Classe | Evidência |
|---|---|---|
| `make reproduce` | IMPLEMENTADO | PR #213; `scripts/reproduce.py` |
| Formatação obrigatória | IMPLEMENTADO | PR #216 (79 arquivos, AST idêntica) |
| `py.typed` e `mypy --strict` no executor | IMPLEMENTADO | PR #215; `.github/workflows/ci.yml:184–185` |
| Módulos experimentais rotulados | IMPLEMENTADO | PR #214; `docs/TRACEABILITY-MASTER.md`, seção Q2 |
| Proteção da `main` | IMPLEMENTADO | Ruleset ativo: PR obrigatória, *checks* obrigatórios (test 3.11/3.12/3.13, golden-regression, judge-regression, security), política *strict*, sem *force-push* nem exclusão. `required_approving_review_count = 0`. |
| CodeQL, dependency review, Dependabot agrupado | IMPLEMENTADO | PRs #196, #201 e #190; workflows `codeql.yml` e `dependency-review.yml` |

### 2.7 Documentação institucional

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Dossiê técnico, proposta a universidade, plano de 12 meses, glossário | PROPOSTO (rascunhos) | PRs #183–#185, #210, #211; `docs/institutional/` | Não pressupõem parceria nem endosso; precisam acompanhar o estado real a cada release |
| Licença Apache-2.0, NOTICE e registro de propriedade intelectual prévia | IMPLEMENTADO | PR #175 | — |

## 3. PRs relevantes e estado atual

| PR | Conteúdo | Situação |
|---|---|---|
| #225 | DEC-012: decisões 1–4 da ADR-010 e §15.1 da ADR-009 | Mesclada por squash; perguntas 5–7 permanecem abertas |
| #232 | Estrato `rectified` (`rgc-eval/0.3.0`) | Aberta; política para campo ausente não decidida |
| #235 | Status e CHANGELOG | Fechada sem merge; conteúdo coberto pelas PRs #230 e #234 |
| #236 | ADR-010 fase 1 | Mesclada após #225; biblioteca pura, sem API/storage/implantação |
| #241 | Proposta de desenho estatístico do RGC | Aberta; checks precisam ser corrigidos/confirmados e escolhas estatísticas são não delegadas |
| #242 | Auditoria técnica desde v0.5.0 | Esta PR; F-01 atualizado e revisão documental em andamento |
| #245 | Regra de autoria e rotulagem de pareceres | Mesclada por squash; checks da cabeça estavam verdes |
| #246 | Transparência sobre apoio automatizado | Aberta; checks conferidos no SHA da cabeça, aguarda ordem de merge |
| #247 | README alinhado à evidência | Aberta; checks conferidos no SHA da cabeça, aguarda ordem de merge |
| #248 | Escopo de módulos experimentais | Aberta; CI inicial falhou por linhas longas nos docstrings; correção enviada, revalidar SHA final |
| #249 | Fonte única de status | Aberta; checks conferidos no SHA da cabeça, aguarda ordem de merge |
| #189 | Dependabot: `transformers` < 6 | Aberta; não mesclar sem revisar o impacto da faixa `<6` nos testes |

## 4. Achados

| ID | Severidade | Achado | Recomendação | Decisão |
|---|---|---|---|---|
| F-01 | Alta (governança) | Os comentários da conta Ayorinha identificados nesta rodada que apareciam como “Revisão independente” foram produzidos de forma automatizada e publicados pela conta do mantenedor; os rótulos desses comentários foram corrigidos para declarar essa natureza. Eles não constituem revisão humana independente. **A revisão humana independente das PRs desde a v0.5.0 permanece pendente.** | Designar revisor humano independente com conta própria e revisar o SHA exato das PRs de código desde a v0.5.0 antes de alegar revisão independente. Manter os pareceres automatizados identificados pela linha padrão. | Anderson (decisão não delegada) |
| F-02 | Alta (segurança) | A aplicação sobe sem autenticação por padrão (`auth.py:24`). O Compose corrige isso, mas uma execução direta com `uvicorn` exposta à rede fica aberta. | Avaliar um modo de produção que recuse iniciar com `off` quando ligado a interface não local, ou um aviso explícito na inicialização. | Mantenedor |
| F-03 | Alta (reprodutibilidade) | Sem `uv.lock` nem digest da imagem base. | Decidir a DEC-001 e implementar em PRs pequenas. | Mantenedor (DEC-001) |
| F-04 | Alta (científica) | Ambiguidade no critério de concordância e baixo poder de H1 se avaliada só no conjunto oculto (~90 casos). | Ver PR #241; decidir antes do congelamento. | Mantenedor |
| F-05 | Média (governança) | DEC-007 e DEC-008 com dois significados (release e RGC). Mitigado por qualificadores (PR #231). | Renumerar ou manter os qualificadores. | Mantenedor |
| F-06 | Média (CI) | A matriz histórica relata uma falha de Schemathesis não reproduzida. Os runs consultados para o SHA `a2562c1f9aeb12df446ddc22a718314a03f3fab1` (#234) e `0fc123f9f8331677acc4bcec00f0d97bca0d1351` (#245) terminaram com sucesso; não foi localizado artefato com caso falsificador, e o workflow não publica relatório como artefato. | Issue [#250](https://github.com/Ayorinha/ayorai-opensearch/issues/250): anexar o run realmente falho e preservar stdout/stderr e exemplo reproduzível numa PR separada; não alterar seed/filtros sem reproduzir. | Investigação aberta; hipótese não confirmada |
| F-07 | Média (auditabilidade) | O log atual é evidência operacional, não prova de integridade (ADR-010, R1 e R2). | Não descrever o sistema como "auditável de forma verificável" até a fase 3 estar implantada. | — |
| F-08 | Baixa | O ruleset não exige aprovação de revisão (`required_approving_review_count = 0`); a revisão independente depende de disciplina, não de bloqueio técnico. | Considerar 1 aprovação obrigatória quando houver revisor com conta própria. | Mantenedor |

## 5. Decisões pendentes do mantenedor

1. Política de ausência do campo `rectified` (PR #232).
2. Critério de concordância, partição de H1 e bootstrap agrupado (PR #241).
3. DEC-001: `uv.lock` e digest da imagem.
4. Renumeração de DEC-007 e DEC-008 ou manutenção dos qualificadores.
5. ADR-010, perguntas 5–7 (escritor, testemunhas, carimbo do tempo), antes da fase 2.
6. Tratamento de F-01 e F-02 antes da v0.6.0.

## 6. Estrutura proposta para o manual técnico modular

Cada módulo cita o commit e a classe de maturidade da matriz acima; nada é descrito como existente sem evidência.

1. **Visão geral e limites de responsabilidade:** o que o sistema faz e não faz; o LLM não é autoridade factual.
2. **Arquitetura:** entrada → recuperação → posição (*stance*) → Judge 2.0 → saída; módulos experimentais fora do escopo verificado.
3. **Judge 2.0:** regras, gates, vereditos, abstenção, canonização RFC 8785, `input_sha256`, `output_sha256` e `rules_sha256`.
4. **API:** contratos `r1-a` e `r2-a`, erros, autenticação, request ID, limites, OpenAPI.
5. **Operação:** instalação, Docker, configuração, diagnóstico, recuperação.
6. **Segurança e privacidade:** modelo de ameaça, logs, LGPD, limites conhecidos.
7. **Reprodutibilidade:** Golden, manifestos, `make reproduce`, CI.
8. **Avaliação:** Golden v0 e v0.1 lado a lado; benchmark RGC (protocolo, pré-registro, estado).
9. **Registro de auditoria:** estado atual, ADR-010, fases.
10. **Governança:** decisões, ADRs, regras de merge e de release.

## 7. Reprodução desta auditoria

```bash
git log --format='%h %p %s' e9eccb5..ab13f73        # 58 commits, todos com um pai
pytest -q                                          # 658 aprovados em ab13f73 (local)
gh api repos/Ayorinha/ayorai-opensearch/commits/ab13f737236d649587051783dd0c5d6e8832178e/check-runs
gh api repos/Ayorinha/ayorai-opensearch/rulesets
```

Esta auditoria descreve o estado em `ab13f73`. Não deve ser lida como prova do estado de commits posteriores.
