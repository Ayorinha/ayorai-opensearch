# TRACEABILITY MASTER — AYORAI ATTRACTOR

**Estado:** [PROPOSTO] matriz documental para revisão.  
**Base:** main após PR #119, commit `c4dc36162d8231d78535d1ca1cb00bfdefb9fd4c`.  
**Escopo desta PR:** somente documentação; nenhum código, teste, fixture, Golden ou manifesto alterado.

## Regras de classificação

- **[VERIFICADO]** confirmado por execução ou consulta direta, com fonte indicada.
- **[DECLARADO]** consta em ADR, documentação ou relato, sem verificação independente aqui.
- **[PROPOSTO]** trabalho futuro ou decisão pendente.
- Cada linha contém requisito, ADR/especificação, código, teste, evidência, status e limitação.
- Não marcar “implementado” sem caminho real de código, teste correspondente e evidência. Se não houver teste, escrever **sem teste**.

## 1. Perguntas de auditoria

**Nota de fidelidade:** a especificação mestra canônica com a seção 1.1 e sua lista literal de 20 perguntas não foi localizada na árvore de arquivos da main consultada. Para não inventar uma transcrição, esta é uma lista operacional derivada do Prompt Mestre v3, não uma cópia literal. A lista deve ser comparada com o documento-fonte antes de ser considerada transcrição fiel.

| # | Pergunta de auditoria | Código | Teste | Status / limitação |
|---:|---|---|---|---|
| 1 | Toda afirmação factual é ligada a evidência ou marcada como não suportada? | `src/ayorai_attractor/verification/claim_pipeline.py` | `tests/verification/test_claim_pipeline.py` | [DECLARADO]; cobertura depende dos caminhos testados. |
| 2 | LLM, mocks e caches derivados de LLM são excluídos da independência epistêmica? | `src/ayorai_attractor/evidence/graph.py` | `tests/test_evidence_graph.py`; `tests/test_evidence_graph_properties.py` | [DECLARADO]; metadados de origem podem limitar a conclusão. |
| 3 | VERIFIED exige evidência independente, concordância e proveniência completa? | ADR-002; `src/ayorai_attractor/verification/judge.py` | `tests/test_verification_judge.py` | [DECLARADO]; não prova todos os cenários possíveis. |
| 4 | O Judge é a única autoridade do veredito? | ADR-002; `src/ayorai_attractor/verification/judge.py`; `src/ayorai_attractor/evidence/core.py` | `tests/test_verification_judge.py`; **sem teste de exclusividade da autoridade** | [RISCO Fase 1]: `EvidenceStore.status()` calcula status próprio e atua como segunda autoridade. |
| 5 | A agregação global respeita a precedência de vereditos? | ADR-002 §4; `src/ayorai_attractor/verification/judge.py` | `tests/test_verification_judge.py` | [DECLARADO]; §4 será substituída pelo futuro ADR-009. |
| 6 | No-answer e out-of-scope resultam em abstenção sem veredito global indevido? | ADR-002 §5; `src/ayorai_attractor/verification/claim_pipeline.py` | `tests/verification/test_claim_pipeline.py` | [DECLARADO]; restrito aos casos cobertos. |
| 7 | Documentos com prompt injection são tratados como dados, não instruções? | ADR-002 §6 | `src/ayorai_attractor/verification/claim_pipeline.py` | `tests/verification/test_claim_pipeline.py`; `tests/test_judge_evaluation.py` | [DECLARADO]; baseline antigo não prova robustez geral. |
| 8 | Números e datas seguem regras determinísticas e locale da fonte? | ADR-002 §7–7.2; ADR-006 | `src/ayorai_attractor/verification/judge.py` | `tests/test_verification_judge.py`; `tests/test_judge_evaluation.py` | [DECLARADO]; limitado aos locales/casos testados. |
| 9 | Golden v0 é fechado por caso e seus artefatos permanecem congelados? | ADR-002 §7.1 | `evals/golden/v0.jsonl`; `evals/corpus/documents.jsonl`; `evals/golden/MANIFEST.json` | `tests/test_judge_evaluation.py`; workflows Golden | [VERIFICADO por relato do Cláudio]; hashes informados preservados. Não mede recuperação geral. |
| 10 | Um replay verifica a integridade do bundle e reproduz o digest? | Prompt Mestre §5.4 | `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py` | `tests/test_replay.py`; `tests/test_replay_store.py` | [DECLARADO]; replay integral end-to-end precisa de prova adicional. |
| 11 | O namespace oficial é resolvido sem sombrear namespaces externos? | ADR-001 | `src/ayorai_attractor/` | `tests/test_namespace.py` | [VERIFICADO: arquivos existem]; status da ADR-001 desatualizado; decisão do mantenedor pendente. |
| 12 | Recuperação e fetcher preservam proveniência e respeitam limites/termos? | Prompt Mestre §3/L2 | `src/ayorai_attractor/providers/`; `src/ayorai_attractor/evidence/` | **sem teste único do fluxo completo** | [PARCIAL]; não comprovados em conjunto todos os controles de fetch. |
| 13 | Orquestração impõe orçamento, isolamento e autonomia limitada? | Prompt Mestre §3/L4 | `src/ayorai_attractor/orchestrator.py`; `src/ayorai_attractor/agents/` | **sem teste único de todos os controles** | [PARCIAL]; testar cada fronteira separadamente. |
| 14 | A síntese final passa por verificação pós-escrita? | Prompt Mestre §3/L5 | `src/ayorai_attractor/verification/claim_pipeline.py` | `tests/verification/test_claim_pipeline.py` | [PARCIAL]; demonstrar todos os caminhos de resposta. |
| 15 | Audit Mode liga claims às citações e verifica suporte factual de ponta a ponta? | Prompt Mestre §3/L6 | Módulo específico não confirmado nesta matriz | **sem teste end-to-end identificado** | [PROPOSTO/PARCIAL]; localizar módulo e teste antes de declarar completo. |
| 16 | Logs e bundles preservam integridade sem expor dados sensíveis? | Prompt Mestre §3/L7–L9 | `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/observability/` | `tests/test_replay.py`; **sem teste dedicado de redação de PII identificado** | [PARCIAL]; integridade não prova privacidade dos logs. |
| 17 | Segurança cobre injection, isolamento de ferramentas e supply chain? | Prompt Mestre §3/L8 | `src/ayorai_attractor/security/`; `.github/workflows/` | Vincular teste a cada controle OWASP ASI; **sem teste único abrangente** | [PARCIAL]; CI/CodeQL verde não prova todos os riscos. |
| 18 | Avaliação compara o sistema ao baseline sem alterar Golden após observar resultados? | Prompt Mestre §3/L10; `docs/eval/BASELINE-v0.md` | `tests/test_judge_evaluation.py`; checks `golden-smoke` e `golden-regression` | [VERIFICADO por docs/checks identificados]; baseline constante não prova capacidade geral. |
| 19 | Promoções de prompt/modelo exigem valset separado e gates de qualidade/segurança? | Prompt Mestre §3/L11 | Módulo de promoção não confirmado | **sem teste de promoção GEPA identificado** | [PROPOSTO]; não declarar self-improvement com gates implementado. |
| 20 | API, CLI, MCP, multi-tenancy, SLO e governança estão comprovados por contratos e testes? | Prompt Mestre §3/L12–L14 | `src/ayorai_attractor/`; `docs/security/` | **sem teste único para o conjunto integral** | [PARCIAL]; cada interface/controle precisa de linha e prova própria. |

## 2. Matriz principal de rastreabilidade

| Requisito | ADR / referência | Arquivo de código | Teste | Evidência | Status | Limitação |
|---|---|---|---|---|---|---|
| Namespace isolado | ADR-001 | `src/ayorai_attractor/` | `tests/test_namespace.py` | Check `namespace-compatibility` e teste presente | [VERIFICADO: artefatos presentes] | Status declarado na ADR-001 desatualizado. |
| Judge determinístico | ADR-002 §1–3 | `src/ayorai_attractor/verification/judge.py` | `tests/test_verification_judge.py` | ADR e teste no repo | [DECLARADO] | Não inferir cobertura além dos casos testados. |
| Agregação global | ADR-002 §4 | `src/ayorai_attractor/verification/judge.py` | `tests/test_verification_judge.py` | `docs/eval/TRACEABILITY.md` | [DECLARADO] | Futuro ADR-009 substituirá §1 e §4; ainda não redigido. |
| Evidência e independência | ADR-002 §2–3; ADR-005 | `src/ayorai_attractor/evidence/graph.py` | `tests/test_evidence_graph.py`; `tests/test_evidence_graph_properties.py` | Testes e matriz R1 existente | [DECLARADO] | Dependência da qualidade dos metadados de origem. |
| Pipeline de claims | ADR-004 | `src/ayorai_attractor/verification/claim_pipeline.py` | `tests/verification/test_claim_pipeline.py` | Testes de pipeline presentes | [DECLARADO] | Verificar todos os caminhos de API antes de afirmar cobertura completa. |
| Replay e digest | Prompt Mestre §5.4; R20 | `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py` | `tests/test_replay.py`; `tests/test_replay_store.py` | Código usa JSON canônico e SHA-256 | [DECLARADO — limitação reportada] | **PR 0.9:** `content_sha256` informado como não reprodutível; pendente de teste determinístico e prova ligada a commit. |
| Exclusividade do Judge | ADR-002 | `src/ayorai_attractor/verification/judge.py`; `src/ayorai_attractor/evidence/core.py` | **sem teste dedicado para exclusividade da autoridade** | `EvidenceStore.status()` calcula `VerificationStatus` próprio | [RISCO Fase 1] | Segunda autoridade de veredito; corrigir em etapa separada. |
| Golden v0 e manifesto | ADR-002 §7.1 | `evals/golden/v0.jsonl`; `evals/corpus/documents.jsonl`; `evals/golden/MANIFEST.json` | `tests/test_judge_evaluation.py`; workflows Golden | Hashes informados pelo Cláudio; checks da PR #119 consultados | [VERIFICADO por fontes identificadas] | Não editar artefatos congelados nem resultados históricos. |
| Baseline legado | `docs/eval/BASELINE-v0.md` | `src/ayorai_attractor/verification/judge.py` | `tests/test_judge_evaluation.py` | Baseline: 13/30 corretos; 43,3333% | [VERIFICADO na documentação do baseline] | Predição PARTIALLY_SUPPORTED em 30/30; acurácia igual à classe majoritária, sem evidência de capacidade geral. |
| Segurança e supply chain | Prompt Mestre §3/L0/L8 | `.github/workflows/`; `src/ayorai_attractor/security/` | Workflows e testes específicos por controle | Checks da PR #119 consultados no GitHub | [PARCIALMENTE VERIFICADO] | Resultado vale para o commit consultado; não comprova toda cobertura OWASP ASI. |
| Audit Mode completo | Prompt Mestre §3/L6 | Módulo específico não confirmado | **sem teste end-to-end identificado** | Requisito documentado | [PROPOSTO/PARCIAL] | Localizar implementação e teste antes de marcar como implementado. |
| OpenSearch híbrido / reranking | Prompt Mestre §3/L2 | `src/ayorai_attractor/providers/`; `src/ayorai_attractor/evidence/` | **sem teste único do fluxo completo** | Estrutura e docs | [PARCIAL] | Validar BM25+kNN+RRF+reranking ponta a ponta. |
| Observabilidade sem PII | Prompt Mestre §3/L9 | `src/ayorai_attractor/observability/` | **sem teste dedicado de redação de PII identificado** | Módulos de observabilidade | [PARCIAL] | Não declarar privacidade de logs sem teste explícito. |
| Promoção GEPA com gates | Prompt Mestre §3/L11 | Módulo não confirmado | **sem teste de promoção identificado** | Requisito futuro | [PROPOSTO] | Exige valset separado, gates e registro reproduzível. |
| API, CLI, MCP e Studio | Prompt Mestre §3/L12 | `src/ayorai_attractor/` | **sem teste único para todas as interfaces** | Árvore do repositório | [PARCIAL] | Rastrear cada contrato individualmente. |
| Multi-tenant, SLO e governança | Prompt Mestre §3/L13–L14 | `src/ayorai_attractor/`; `docs/security/`; `docs/` | **sem teste único para o conjunto integral** | Documentação e estrutura | [PARCIAL] | Documentação não prova isolamento, quotas, SLO ou conformidade operacional. |

## 3. Princípios das seções 2 a 7 do Prompt Mestre v3

| Princípio | Referência | Código | Teste | Evidência | Status | Limitação |
|---|---|---|---|---|---|---|
| Estado real separado do declarado | §2; `docs/PROGRESS.md`; `docs/STATUS.md` | Por requisito nas tabelas acima | Por requisito nas tabelas acima | Esta matriz registra divergências | [EM ANDAMENTO] | Documentação pode ficar desatualizada. |
| Cada camada deve ter contrato, implementação, testes, métricas e docs | §3, L0–L14 | Módulos `src/ayorai_attractor/` | Testes associados por requisito | Árvore real do repo | [PARCIAL] | Nem todas as camadas têm prova integral. |
| Ordem do roadmap não deve ser pulada | §4 | N/A — processo | **sem teste automatizado** | Histórico de PRs | [DECLARADO] | Regra de processo, não comportamento runtime. |
| Arena honesta, conjunto congelado e revisão humana | §5 | `evals/`; `docs/eval/` | Testes de avaliação disponíveis | Baseline e Golden v0 | [PARCIAL] | Não alegar comparação externa sem dados/scripts/versionamento reproduzíveis. |
| Não selecionar perguntas após ver resultados nem alegar superioridade fora do escopo | §5.6 | N/A — governança | **sem teste automatizado** | Regra documental | [DECLARADO] | Exige revisão humana e disciplina de versionamento. |
| PRs documentam motivação, risco, rollback e teste | §6 | N/A — processo | **sem teste automatizado** | Descrição de PR | [DECLARADO] | Não há validação automática de completude identificada. |
| Testes adequados por tipo de mudança | §6 | Por requisito | Testes listados acima | Suíte e CI | [DECLARADO/PARCIAL] | Ausências permanecem explicitamente “sem teste”. |
| mypy strict bloqueante em código novo | §6 | Código novo | Workflow de typing | PR #119 tinha check `typecheck-strict (non-blocking)` | [PARCIAL] | Check não bloqueante não prova exigência bloqueante. |
| Smoke eval sem regressão | §6 | `evals/`; workflows | `golden-smoke`; `golden-regression` | Checks da PR #119 concluídos com sucesso | [VERIFICADO para o SHA da PR #119] | Não se transfere automaticamente a commits posteriores. |
| ADR para decisões de arquitetura | §6; `docs/adr/README.md` | N/A — documentação | **sem teste automatizado** | Índice ADR da PR #119 | [VERIFICADO no GitHub] | ADR-009 pendente; ADR-001 exige decisão de status. |
| Conquistas somente com prova | §6 | N/A — documentação | **sem teste automatizado** | Links de runs/releases | [DECLARADO] | Não registrar conquista apenas por texto descritivo. |
| Respostas classificam [VERIFICADO]/[DECLARADO]/[PROPOSTO] e não inventam métricas | §7; regras de honestidade v3 | N/A — processo | **sem teste automatizado** | Política documental e relatórios com fontes | [DECLARADO] | Depende de disciplina operacional em cada relatório. |

## 4. Achados reservados para etapas futuras

1. **ADR-001:** status declarado desatualizado; atualização pendente de decisão do mantenedor. Não editar nesta PR.
2. **ADR-009:** ADR-002 §1 e §4 serão substituídas pelo futuro ADR-009, ainda não redigido. Não antecipar sua decisão.
3. **EvidenceStore.status() — Fase 1:** `src/ayorai_attractor/evidence/core.py` calcula status próprio. Registrar como segunda autoridade de veredito; não há teste dedicado de exclusividade identificado. Não alterar nesta PR.
4. **content_sha256 — PR 0.9:** reprodutibilidade reportada como pendente. Só marcar resolvido com teste determinístico, execução reproduzível e evidência ligada ao commit.
5. **Baseline legado:** PARTIALLY_SUPPORTED em 30/30 claims com veredito global; 13/30 corretos (43,3333%), igual à classe majoritária. Não representa capacidade geral de verificação.
6. **20 perguntas da seção 1.1:** localizar a especificação mestra canônica e comparar sua redação com a lista operacional da seção 1 antes de alegar transcrição literal.

## 5. Manutenção

- Atualizar a matriz na mesma PR que altera o requisito correspondente.
- Usar caminhos reais de código e teste. Se não houver teste, escrever “sem teste”.
- Nunca declarar “implementado” sem teste e evidência.
- Anexar SHA, comando ou URL de check-run para alegações de CI, testes e métricas.
- Preservar Golden, manifestos, hashes e resultados históricos.
- Esta matriz documenta rastreabilidade; não substitui ADRs nem aprova automaticamente arquitetura pendente.
