# Auditoria técnica — AYORAI ATTRACTOR desde a v0.5.0


> **Atualização datada (2026-10-21):** a tabela abaixo registra o estado do protocolo no momento da auditoria original. A Emenda 6 foi posteriormente incorporada pela PR #288 (`5a587ecb64abc6359c8fe36b8194b67dee3edda9`), registrando baseline B primária e A descritiva também no pré-registro. A referência a “Emendas 1–5” abaixo é histórica; o protocolo atual documenta a Emenda 6 e continua não congelado.

**Desvios de formato de commit registrados:** [registro datado de mensagens fora do padrão de squash](PROCESS-DEVIATIONS-2026-10-21.md). O histórico Git foi preservado.

| Campo | Valor |
|---|---|
| Versão de referência | v0.5.0, publicada em 2026-10-13 (tag no commit `e9eccb50e4904b8f33004a414a5666477378c67a`; DOI 10.5281/zenodo.23344005) |
| Estado auditado | `main` em `d8411d90f8905442ac02568cc9179ce42afec69a` (2026-10-18) |
| Intervalo | 80 commits desde a tag v0.5.0 até `d8411d90f8905442ac02568cc9179ce42afec69a`, conforme compare do GitHub; contagem de commits, não de PRs |
| Solicitante | Anderson Leon Ayora (mantenedor) |
| Natureza | Documento de engenharia. Não altera código, decisões, ADRs, regras, Golden, manifestos ou hashes. |

## 0. Método e regra de evidência

Nenhum item é classificado como implementado sem **código na `main`**, **teste que o exercita** e **execução registrada**. Fontes consultadas:

1. Compare da tag v0.5.0 (`e9eccb5`) até a `main` auditada (`d8411d9`): 80 commits, conforme compare do GitHub. A estrutura de pais não foi revalidada por clone local nesta sessão.
2. API REST do GitHub: PRs mescladas e abertas, check-runs, ruleset `Protecao-main-ATTRACTOR`, releases e comentários.
3. Última execução local declarada: **658 testes aprovados em `ab13f737`** (Python 3.13.16, `pytest -q`), resultado histórico, não reexecutado neste ciclo. Para o SHA auditado `d8411d90f8905442ac02568cc9179ce42afec69a`, os seis checks obrigatórios e os demais checks de CI não específicos de branch terminaram com sucesso. O job `rgc-design-simulation` é intencionalmente específico da branch da PR #241; a execução separada passou no SHA `0e515e9c76328c7023b24394459acc21d9e2bd0a` (run `39091010493`). Não foi feita execução local nesta sessão.
4. Para o SHA `d8411d90f8905442ac02568cc9179ce42afec69a`, `Security`, `CodeQL` e os seis checks obrigatórios terminaram com sucesso; a simulação estatística foi executada separadamente no SHA da PR #241. Essas evidências valem para os SHAs citados, não para cabeças de PR diferentes.
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
| Registro de auditoria verificável (ADR-010) | IMPLEMENTADO — LIMITADO | ADR-010 está “Accepted in part”; DEC-012 foi registrada em #225 e a biblioteca pura da fase 1 com vetores foi mesclada em #236. O armazenamento atual **não** é à prova de adulteração; não há API de gravação, persistência de eventos, checkpoints assinados nem serviço de log verificável implantado. |
| Benchmark RGC PT-BR | PENDENTE | Fontes capturadas; Emendas 1–5 registradas; DEC-014 define baseline B primário e A descritivo. **Protocolo não congelado. Nenhum resultado de benchmark PT-BR.** |
| Reprodutibilidade e CI | IMPLEMENTADO | `make reproduce`, seed fixa no Schemathesis, `ruff format` obrigatório, `mypy --strict` no executor, `py.typed`. |
| Cadeia de suprimentos | PENDENTE | Sem `uv.lock`, sem digest de imagem, sem SBOM, sem assinatura de release (DEC-001 pendente). |
| Governança e documentação | IMPLEMENTADO — LIMITADO | Status reconciliado (#230, #231, #234). Comentários antes rotulados como revisão independente foram reidentificados como revisões automatizadas publicadas pelo mantenedor; a revisão humana independente das PRs desde a v0.5.0 continua pendente (F-01). |

## 2. Matriz de auditoria

### 2.1 Judge determinístico e contrato da API

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Evidências `r2-a` com `canonical_url` são adjudicadas, sem `SCHEMA_VIOLATION` | IMPLEMENTADO | PR #192 (issue #182); testes de regressão na PR | — |
| Regras do Judge distribuídas no pacote | IMPLEMENTADO | PR #224; `src/ayorai_attractor/verification/judge2/__init__.py:26`; `tests/verification/test_judge2_packaged_rules.py` (4 testes: identidade de bytes, `rules_sha256` canônico, *checkout* × instalado) | Duas cópias byte a byte idênticas; o teste falha se divergirem |
| Regras, Golden e hashes congelados inalterados desde a v0.5.0 | IMPLEMENTADO | `golden-regression`, `judge-regression` e `golden-smoke` verdes no SHA auditado `d8411d90f8905442ac02568cc9179ce42afec69a` | — |
| Remoção de `ResponseStatus`, `verification`, `confidence` e do caminho `r1-a` | PENDENTE | Adiada para v0.6.0 pela DEC-008 (release) | Ainda presentes; nada removido |

### 2.2 API, autenticação e privacidade

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Autenticação por API key | IMPLEMENTADO — LIMITADO | PRs #252 e #256; `src/ayorai_attractor/api/auth.py`, `tests/test_api_auth.py`; checks verdes nos SHAs mesclados. | `api_key` é o padrão e a inicialização falha fechada sem configuração válida; `--lifespan on` assegura a validação no arranque. `/health` permanece público; não há rate limiting, expiração ou revogação individual. |
| Autenticação dentro do contêiner | IMPLEMENTADO | PR #226; `.github/workflows/docker.yml`: `/health` público, 401 sem chave e com chave inválida, 200 com chave válida | Credenciais efêmeras geradas no CI |
| `X-Request-ID` e log de acesso JSON | IMPLEMENTADO | PRs #221 e #260; `src/ayorai_attractor/api/request_context.py:14` (padrão `[A-Za-z0-9-]{1,64}`); `tests/test_api_request_context.py` e `tests/test_api_uvicorn_access_log.py` (Uvicorn real) | O evento registra request ID, método, rota, status e duração; não registra corpo nem query string. O teste real verifica que um segredo em query string não aparece na saída. Não há garantia formal contra todo futuro campo adicionado. |
| Limite de corpo HTTP (413) | IMPLEMENTADO | PRs #218 e #223; `src/ayorai_attractor/api/app.py:92,95`; `tests/test_api.py:200–223`; `tests/test_api_uvicorn_body_limit.py` | — |
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
| ADR-010 (log Merkle C2SP) | ACCEPTED IN PART / IMPLEMENTADO — LIMITADO | PR #220 mantém o desenho; DEC-012 foi registrada em #225; a biblioteca pura da fase 1 foi mesclada na #236 | Sem persistência, API de gravação, checkpoints assinados ou implantação; o log verificável não está implementado como serviço |
| Fase 1: hashing RFC 6962, provas e compromissos com sal | IMPLEMENTADO — LIMITADO | PR #236 mesclada; vetores e testes em `tests/auditlog/`; checks obrigatórios verdes no SHA revisado antes do merge | Biblioteca pura. Não constitui log implantado. |
| Fases 2–4 (checkpoints assinados, gravação, testemunhas, carimbo do tempo) | PENDENTE | ADR-010, perguntas 5–7 abertas | — |

### 2.5 Benchmark RGC em português

| Item | Classe | Evidência | Limite |
|---|---|---|---|
| Política de fontes (DEC-002) | IMPLEMENTADO | PR #176; `docs/DECISIONS-APPROVED.md` | Não é parecer jurídico |
| Captura byte a byte e texto derivado da Resolução Anatel 765/2023 e de duas retificações | IMPLEMENTADO | PRs #177 e #178; `evals/ptbr/sources/`; `evals/ptbr/SOURCES-REGISTRY.json`; `tests/test_source_artifacts.py`, `test_source_derived_text.py`, `test_sources_registry.py` | A captura não interpreta vigência |
| Pré-registro | PROPOSTO | PR #174; `docs/eval/PREREGISTRATION-RGC-v1.md`, marcado **[PROPOSTO]** | Ver a proposta estatística (PR #241) |
| Protocolo com Emendas 1–5 | IMPLEMENTADO como documento; **não congelado** | `docs/eval/PROTOCOL-GOLDEN-V1.md`; PRs #193, #205, #227 e #241 | DEC-014/Emenda 5 define apenas os baselines; o congelamento exige registro explícito separado do mantenedor. |
| Executor `rgc-eval/0.3.0` (abstenção, átomos e estrato `rectified`) | IMPLEMENTADO — LIMITADO | PRs #179, #195, #203 e #232; `evals/ptbr/rgc_eval.py:56–58`; `tests/test_rgc_eval_runner.py` (fixtures sintéticas) | Marcado [PROPOSTO]; validado apenas com dados sintéticos, sem resultado de benchmark. |
| Estrato `rectified` (DEC-011, Emenda 4) | IMPLEMENTADO | PR #232, mesclada; ausência de `rectified` equivale a `false` e o campo é validado mesmo em casos excluídos ou sem rótulo. | Nenhum resultado de benchmark foi produzido. |
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
| #232 | Estrato `rectified` (DEC-011, Emenda 4) | Mesclada por squash; decisão sobre ausência do campo registrada como `false`; nenhum resultado de benchmark incluído |
| #235 | Status e CHANGELOG | Fechada sem merge; conteúdo coberto pelas PRs #230 e #234 |
| #236 | ADR-010 fase 1 | Mesclada após #225; biblioteca pura, sem API/storage/implantação |
| #241 | Proposta de desenho estatístico do RGC | Mesclada por squash; DEC-014 e Emenda 5 registradas; simulação sintética executada no run `39091010493`, SHA `0e515e9c76328c7023b24394459acc21d9e2bd0a`, com artefato `rgc-design-simulation-eb9994988a68b50021ea2454e2e10553bf0f9516`; protocolo não congelado |
| #242 | Auditoria técnica desde v0.5.0 | Esta PR; documento atualizado para `main` `d8411d90f8905442ac02568cc9179ce42afec69a`; checks da cabeça final ainda exigidos antes do merge |
| #245 | Regra de autoria e rotulagem de pareceres | Mesclada por squash; checks da cabeça estavam verdes |
| #246 | Transparência sobre apoio automatizado | Mesclada por squash; checks verdes no SHA final |
| #247 | README alinhado à evidência | Mesclada por squash após revisão e checks verdes |
| #248 | Escopo de módulos experimentais | Mesclada por squash após correção de E501 e checks verdes no SHA final |
| #249 | Fonte única de status | Mesclada por squash após revisão e checks verdes no SHA final |
| #251 | Atualização da página canônica de status | Mesclada por squash; atualização da página canônica; a versão final de status deste ciclo está reservada à Onda 10 (#255) |
| #253 | Evidência reproduzível de Schemathesis | Mesclada por squash; preserva logs, OpenAPI servido e exemplos Hypothesis para futuras falhas. A issue #250 foi fechada após a correção #259 e permanece sob observação de recorrência. |
| #254 | Correção de estado DEC-012 | Mesclada por squash; índice atualizado após a #225 |
| #255 | Reconciliação da fonte única de status | Aberta; reservada para a Onda 10, último merge deste ciclo, com `docs/STATUS.md` a atualizar após as Ondas 2–5 |
| #256 | Inicialização fail-closed sob Uvicorn | Mesclada por squash; `--lifespan on` assegura validação de autenticação no arranque |
| #257 | Comportamento real dos agentes em runtime | Mesclada por squash; documentação limitada ao comportamento verificado |
| #258 | DEC-013 — autorização deste ciclo | Mesclada por squash; escopo e dispensa de revisão independente registrados; F-01 permanece aberto |
| #259 | Correção da configuração de Schemathesis em `/v1/audit` | Mesclada por squash; issue #250 fechada após a correção e sob observação de recorrência |
| #260 | Log de acesso estruturado sob Uvicorn | Mesclada por squash; teste com servidor real e supressão do log padrão para evitar query strings |
| #261 | Integridade documental automática | Mesclada por squash; teste de links relativos/âncoras e correção da âncora DEC-010 |
| #252 | Autenticação fail-closed por padrão | Mesclada por squash; padrão `api_key`, falha fechada e rejeição de cabeçalhos duplicados/mecanismos simultâneos |
| #189 | Dependabot: `transformers` < 6 | Mesclada; workflows passaram no SHA `ff0ca338`, incluindo inferência NLI em CPU com Transformers 5.20.1 e a suíte completa |

## 4. Achados

| ID | Severidade | Achado | Recomendação | Decisão |
|---|---|---|---|---|
| F-01 | Alta (governança) | Comentários automatizados não constituem revisão humana independente. **A revisão humana independente das PRs desde a v0.5.0 permanece pendente.** A DEC-013 dispensou essa revisão apenas para o ciclo de 2026-10-18; a dispensa não encerra F-01. | Designar revisor humano independente com conta própria e revisar o SHA exato das PRs de código desde a v0.5.0 antes de alegar revisão independente. | DEC-013; F-01 permanece aberto |
| F-02 | Alta (segurança) | Resolvido pelas PRs #252 e #256: a aplicação usa `api_key` por padrão, falha fechada sem configuração válida e valida o arranque com `--lifespan on`. | Manter configuração e exemplos alinhados; `/health` continua público e não há rate limiting nem TLS próprio. | Resolvido; checks verdes no SHA auditado |
| F-03 | Alta (reprodutibilidade) | Sem `uv.lock` nem digest da imagem base. | Decidir a DEC-001 e implementar em PRs pequenas. | Mantenedor (DEC-001) |
| F-04 | Alta (científica) | DEC-014 resolveu a definição de baseline: B primário, derivado da partição de desenvolvimento; A é apenas descritivo. A concordância e outras escolhas metodológicas continuam pendentes. | A simulação de #241, SHA `0e515e9c76328c7023b24394459acc21d9e2bd0a`, é sintética; em prevalência muito desbalanceada, acurácia-alvo 0,60 e n=300, P(H1 contra B) foi 0,115 sob independência e 0,085 sob phi-alvo 0,5. Não é benchmark PT-BR. Não congelar o protocolo antes do piloto 02 e das decisões restantes. | DEC-014; definição de baseline decidida |
| F-05 | Média (governança) | DEC-007 e DEC-008 com dois significados (release e RGC). Mitigado por qualificadores (PR #231). | Renumerar ou manter os qualificadores. | Mantenedor |
| F-06 | Média (CI) | A falha histórica de Schemathesis não foi reproduzida nos runs consultados. #253 foi mesclada e preserva stdout/stderr, OpenAPI servido e exemplos Hypothesis para investigações futuras; #259 corrigiu a assimetria do filtro `negative_data_rejection` entre `/v1/opensearch` e `/v1/audit`. | A issue [#250](https://github.com/Ayorinha/ayorai-opensearch/issues/250) foi fechada após a #259 e permanece sob observação de recorrência. Não afirmar que a falha histórica foi reproduzida; se reaparecer, anexar os artefatos preservados. | Correção aplicada; monitorar recorrência |
| F-07 | Média (auditabilidade) | O log atual é evidência operacional, não prova de integridade (ADR-010, R1 e R2). | Não descrever o sistema como "auditável de forma verificável" até a fase 3 estar implantada. | — |
| F-08 | Baixa | O ruleset não exige aprovação de revisão (`required_approving_review_count = 0`); a revisão independente depende de disciplina, não de bloqueio técnico. | Considerar 1 aprovação obrigatória quando houver revisor com conta própria. | Mantenedor |

## 5. Decisões pendentes do mantenedor

1. DEC-001: `uv.lock` e digest da imagem.
2. DEC-003: estado de ADR-001.
3. DEC-004: documentação comercial e nome do repositório.
4. DEC-006: prioridade do motor de stance em português.
5. Renumeração de DEC-007/008 ou manutenção dos qualificadores.
6. ADR-010, perguntas 5–7 (escritor, testemunhas, carimbo do tempo), antes da fase 2.

DEC-011/Emenda 4 e a política `rectified` foram implementadas na #232. DEC-014/Emenda 5 resolveu somente a definição do baseline; protocolo ainda não congelado. F-01 permanece aberto apesar da dispensa de revisão independente neste ciclo; F-02 está resolvido.

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
9. **Registro de auditoria:** ADR-010 “Accepted in part”; fase 1 mesclada como biblioteca pura em #236; sem serviço de log verificável implantado.
10. **Governança:** decisões, ADRs, regras de merge e de release.

## 7. Reprodução desta auditoria

```bash
git log --format='%h %p %s' e9eccb5..d8411d9        # compare do GitHub: 80 commits; sem clone local nesta sessão
gh api repos/Ayorinha/ayorai-opensearch/commits/d8411d90f8905442ac02568cc9179ce42afec69a/check-runs
# O resultado local de 658 testes em ab13f737 é histórico, não execução neste SHA.
gh api repos/Ayorinha/ayorai-opensearch/rulesets
```

Esta auditoria descreve o estado da `main` em `d8411d90f8905442ac02568cc9179ce42afec69a` (2026-10-18). Não deve ser lida como prova do estado de commits posteriores.
