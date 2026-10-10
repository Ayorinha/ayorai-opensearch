# TRACEABILITY MASTER — AYORAI ATTRACTOR

**Estado:** [PROPOSTO] matriz documental em revisão; não autoriza, por si só, declaração de implementação.
**Especificação canônica:** *AYORAI ATTRACTOR — ESPECIFICAÇÃO MESTRA DO LABORATÓRIO BRASILEIRO DE AUDITORIA, BENCHMARK E RASTREABILIDADE DE INTELIGÊNCIA ARTIFICIAL*; identificador `AYORAI-ATTRACTOR-BAL`; versão `1.0.0`.
**Origem da especificação:** documento-fonte fornecido pelo mantenedor; ainda não versionado neste repositório. Proposta futura: versionar em `docs/spec/`, mediante decisão do mantenedor.
**Base da PR:** `main` após PR #119, commit `c4dc36162d8231d78535d1ca1cb00bfdefb9fd4c`.
**Escopo:** somente documentação. Não alterar código, testes, fixtures, Golden, corpus, manifestos ou hashes congelados.

## Regras de classificação e evidência

- **[VERIFICADO por execução local — Cláudio, commit `d311619`]** significa que o comando foi executado localmente sobre aquele commit. O relato disponível registra `pytest: 348 passed`, os 34 caminhos citados existentes na árvore e os hashes congelados inalterados. Isso **não** valida automaticamente o conteúdo desta revisão nem transfere a verificação para um commit posterior.
- Toda nova afirmação [VERIFICADO] precisa indicar comando, check-run, SHA/commit ou fonte diretamente consultada. Separar execução local, consulta ao GitHub e afirmação declarada por documentação.
- **[DECLARADO]** significa que consta em código/documentação ou foi relatado, mas a alegação específica não foi verificada de forma independente nesta linha.
- **[PARCIAL]** significa que há implementação/teste para parte do requisito, com lacuna explícita.
- **[NÃO IMPLEMENTADO]** ou **[SEM TESTE]** deve ser usado quando aplicável; não preencher lacunas por inferência.
- **[PROPOSTO]** indica trabalho futuro ou decisão pendente.
- Não declarar “implementado” sem apontar código real, teste pertinente e evidência. Existência de arquivo ou teste, isoladamente, não prova o comportamento completo.
- Em cada linha, registrar requisito, referência, caminho de código, teste, evidência/status e limitação. Quando não houver teste pertinente identificado, escrever **sem teste identificado**.

## 1. As 20 perguntas literais da seção 1.1 da especificação canônica

A redação abaixo foi fornecida pelo mantenedor como a seção 1.1 da especificação `AYORAI-ATTRACTOR-BAL` v1.0.0. A especificação ainda não está versionada no repositório. Os mapeamentos técnicos são provisórios e devem ser confirmados contra o código e os testes antes de declarar cobertura.

| # | Pergunta literal | Referência / código candidato | Teste candidato | Status / limitação |
|---:|---|---|---|---|
| 1 | A afirmação avaliada é sustentada pelas evidências disponíveis? | `src/ayorai_attractor/verification/claim_pipeline.py`; Judge | `tests/verification/test_claim_pipeline.py`; `tests/test_verification_judge.py` | [PARCIAL]; confirmar que o teste cobre suporte da afirmação, não apenas presença de evidência. |
| 2 | A citação realmente corresponde ao documento de origem? | `src/ayorai_attractor/verification/excerpt.py` | `tests/verification/test_excerpt_revalidation.py` | [DECLARADO]; mapeamento indicado pelo mantenedor; confirmar execução para o commit revisado. |
| 3 | O trecho citado sustenta toda a afirmação ou apenas parte dela? | Judge e lógica de cobertura da afirmação | ADR-009 ainda não redigido; **sem teste de cobertura integral identificado** | [NÃO IMPLEMENTADO — ADR-009]; o Judge atual não mede cobertura completa; `S=1 → PARTIALLY_SUPPORTED` não resolve cobertura semântica. |
| 4 | Existem evidências que contradizem a conclusão? | `src/ayorai_attractor/verification/judge.py`; grafo de evidências | `tests/test_verification_judge.py`; testes de grafo, se aplicáveis | [PARCIAL]; verificar explicitamente detecção e precedência de evidência contraditória. |
| 5 | As fontes são independentes ou reproduzem uma origem comum? | `src/ayorai_attractor/verification/clusters.py`; `src/ayorai_attractor/evidence/graph.py` | `tests/test_verification_clusters.py`; `tests/verification/test_f11_metadata_rules.py` | [DECLARADO]; a conclusão depende da qualidade e completude dos metadados de proveniência. |
| 6 | O sistema utilizou informações desatualizadas? | Recuperação/fetch e metadados temporais; confirmar caminho concreto | **sem teste específico de atualidade identificado** | [SEM TESTE IDENTIFICADO]; não inferir verificação temporal a partir da existência de timestamps. |
| 7 | A ausência de evidência foi tratada corretamente? | `src/ayorai_attractor/verification/judge.py`; pipeline de claims | `tests/test_verification_judge.py`; `tests/verification/test_claim_pipeline.py` | [PARCIAL]; confirmar casos de ausência, insuficiência e abstenção. |
| 8 | O sistema reconheceu quando deveria se abster? | `src/ayorai_attractor/verification/claim_pipeline.py`; Judge | `tests/verification/test_claim_pipeline.py`; `tests/test_verification_judge.py` | [PARCIAL]; cobertura limitada aos cenários testados. |
| 9 | O resultado permaneceu consistente diante de paráfrases equivalentes? | Normalização e avaliação; confirmar caminho exato | **sem teste específico de invariância a paráfrases identificado** | [SEM TESTE IDENTIFICADO]; não alegar consistência sem conjunto e critério de equivalência versionados. |
| 10 | A decisão pode ser reproduzida com os mesmos artefatos e as mesmas regras? | `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py`; serialização/digest | `tests/test_replay.py`; `tests/test_replay_store.py` | [PARCIAL — PR 0.9]; `content_sha256` foi reportado como não reprodutível; exige correção e prova determinística. |
| 11 | A proveniência dos documentos pode ser verificada? | `src/ayorai_attractor/evidence/`; `src/ayorai_attractor/replay_store.py` | Testes de evidência e replay pertinentes; confirmar cobertura específica | [PARCIAL]; não presumir proveniência integral só porque existe um bundle. |
| 12 | A execução respeitou as restrições de privacidade configuradas? | `src/ayorai_attractor/observability/`; configuração de privacidade a localizar | **sem teste específico de cumprimento das restrições de privacidade identificado** | [SEM TESTE IDENTIFICADO]; não afirmar conformidade LGPD ou ausência de vazamento sem evidência específica. |
| 13 | Alterações no código, nos dados ou nas regras modificaram o resultado? | Replay, avaliação Golden e digests | `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py`; testes de replay pertinentes | [PARCIAL]; integridade de artefatos não demonstra, sozinha, sensibilidade a toda mudança de código/regra. |
| 14 | O sistema é vulnerável a instruções maliciosas inseridas em documentos? | `src/ayorai_attractor/verification/security.py` | `tests/test_verification_response_security.py` | [DECLARADO]; testar no commit revisado; testes específicos não provam imunidade geral a prompt injection. |
| 15 | Um terceiro consegue reconstruir a justificativa técnica do veredito? | Judge, evidências, clusters e replay | Testes de Judge/replay; **sem teste único de reconstrução independente end-to-end identificado** | [PARCIAL]; precisa de procedimento reproduzível por terceiro com artefatos e regras fixados. |
| 16 | O sistema consegue identificar quando a informação disponível é insuficiente? | Judge e pipeline de claims | `tests/test_verification_judge.py`; `tests/verification/test_claim_pipeline.py` | [PARCIAL]; distinguir insuficiência explícita de ausência acidental de dados. |
| 17 | O resultado depende excessivamente de um modelo ou fornecedor específico? | Adaptadores de modelos/provedores e avaliação comparativa | **sem teste específico de dependência de fornecedor identificado** | [SEM TESTE IDENTIFICADO]; exige avaliação cruzada com modelos/provedores e protocolo comparável. |
| 18 | É possível identificar em qual etapa ocorreu uma falha? | Orquestração, pipeline, logs e observabilidade | **sem teste de diagnóstico por etapa identificado** | [NÃO IMPLEMENTADO / NÃO COMPROVADO]; confirmar a implementação antes de alterar o rótulo. |
| 19 | O sistema apresenta desempenho consistente em diferentes categorias de casos? | `src/ayorai_attractor/evaluation/golden.py`; conjuntos de avaliação | Testes de avaliação existentes; **sem evidência de cobertura representativa de todas as categorias** | [PARCIAL]; publicar resultados por categoria, tamanho e composição do conjunto. |
| 20 | As conclusões estatísticas são sustentadas pelo tamanho e pela composição do conjunto avaliado? | `docs/eval/BASELINE-v0.md`; protocolo Golden | `tests/test_judge_evaluation.py`; `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py` | [LIMITAÇÃO DOCUMENTADA]; n=30; intervalos de confiança incluem o baseline. Não generalizar além do conjunto avaliado. |

## 2. Matriz principal de rastreabilidade da especificação canônica

### 2.1 Princípios fundamentais — seção 2

| Requisito | Referência canônica | Código | Teste | Evidência / status | Limitação |
|---|---|---|---|---|---|
| LLM não é autoridade final do veredito | §2.1 — LLM ≠ Judge | `src/ayorai_attractor/verification/judge.py`; `src/ayorai_attractor/evidence/core.py` | `tests/test_verification_judge.py`; **sem teste dedicado de exclusividade da autoridade** | [RISCO — Fase 1]; `EvidenceStore.status()` calcula status próprio | Há risco de segunda autoridade; não corrigir nesta PR documental. |
| Evidência precede conclusão | §2.2 | `src/ayorai_attractor/verification/claim_pipeline.py`; módulos de evidência | `tests/verification/test_claim_pipeline.py` e testes pertinentes de evidência | [PARCIAL]; confirmar relação explícita entre cada conclusão e evidência | A existência de pipeline não prova suporte integral de cada claim. |
| Proveniência integral | §2.3 | `src/ayorai_attractor/evidence/`; `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py` | Testes de evidência/replay; confirmar cobertura ponta a ponta | [PARCIAL]; `content_sha256` pendente de reprodutibilidade (PR 0.9) | Não afirmar proveniência integral até resolver e testar o digest. |
| Separação entre desenvolvimento, avaliação e validação | §2.4 | `evals/`; `docs/eval/` | `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py`; workflows Golden | [PARCIAL]; verificar segregação real dos conjuntos e processos | Golden congelado não prova, sozinho, independência de todos os conjuntos. |
| Transparência sobre limitações | §2.5 | `docs/eval/BASELINE-v0.md`; esta matriz | **sem teste automatizado de completude das limitações** | [DECLARADO]; limitações do baseline e dos requisitos sem teste são registradas | Depende de atualização honesta e contínua da documentação. |

### 2.2 Independência tecnológica — seção 3

| Requisito | Referência canônica | Código / artefato | Teste / evidência | Status | Limitação |
|---|---|---|---|---|---|
| Inventário de dependências e SBOM | §3.2 | Manifestos e workflows de dependências a conferir no repositório | **sem verificação de SBOM anexada a esta linha** | [PENDENTE DE CONFIRMAÇÃO] | Não afirmar SBOM completo sem arquivo, ferramenta, comando e resultado identificados. |
| Modo offline testado com rede bloqueada | §3.3 | Implementação/configuração offline a localizar | **sem teste com rede efetivamente bloqueada identificado** | [SEM TESTE IDENTIFICADO] | Execução sem uso aparente de rede não equivale a teste com rede bloqueada. |
| Modelos nacionais e estrangeiros | §3.4 | Adaptadores e configuração de modelos a conferir | **sem matriz comparativa nacional/estrangeira identificada** | [PENDENTE DE CONFIRMAÇÃO] | Não inferir suporte ou paridade a partir da existência de adaptadores. |

### 2.3 Escopo do benchmark — seção 4

| Requisito | Referência canônica | Código / artefato | Teste / evidência | Status | Limitação |
|---|---|---|---|---|---|
| Escopo, população, exclusões e limites do benchmark explicitados | §4 | `evals/`; `docs/eval/` | `tests/test_judge_evaluation.py`; protocolo e resultados a conferir | [PARCIAL] | Não generalizar além dos casos, categorias e condições documentadas. |
| Baseline legado corretamente contextualizado | §4; `docs/eval/BASELINE-v0.md`, linha 85 | `src/ayorai_attractor/orchestrator.py`; `src/ayorai_attractor/evidence/core.py` (`EvidenceStore.status`); `src/ayorai_attractor/evaluation/golden.py` (`_legacy_prediction`, linhas 156–164) | `tests/test_judge_evaluation.py` | [DECLARADO NA DOCUMENTAÇÃO DO BASELINE]; 13/30 = 43,3333%; PARTIALLY_SUPPORTED em 30/30 | Igual à classe majoritária; não representa evidência de capacidade geral de verificação. |
| Tamanho e composição sustentam as conclusões estatísticas | §4; §7 | `docs/eval/BASELINE-v0.md`; artefatos de avaliação | `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py` | [LIMITAÇÃO DOCUMENTADA] | n=30; intervalos de confiança incluem o baseline; conclusões devem permanecer restritas. |

### 2.4 Arquitetura — seção 5 (itens 5.1 a 5.8)

Os oito itens da arquitetura devem permanecer individualmente rastreáveis. A atribuição abaixo é uma estrutura de auditoria; o nome exato e o escopo de cada item 5.1–5.8 devem ser reconciliados com a especificação-fonte antes de declarar conformidade integral.

| Requisito / etapa | Referência | Código candidato | Teste candidato | Status / limitação |
|---|---|---|---|---|
| Arquitetura 5.1 | Especificação canônica §5.1 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]; não inferir o requisito detalhado sem conferir a fonte. |
| Arquitetura 5.2 | Especificação canônica §5.2 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]. |
| Arquitetura 5.3 | Especificação canônica §5.3 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]. |
| Arquitetura 5.4 — replay / integridade | Especificação canônica §5.4 | `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py` | `tests/test_replay.py`; `tests/test_replay_store.py` | [PARCIAL — PR 0.9]; `content_sha256` reportado como não reprodutível. |
| Arquitetura 5.5 | Especificação canônica §5.5 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]. |
| Arquitetura 5.6 | Especificação canônica §5.6 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]. |
| Arquitetura 5.7 | Especificação canônica §5.7 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]. |
| Arquitetura 5.8 | Especificação canônica §5.8 | `src/ayorai_attractor/` — módulo específico a confirmar | **sem teste mapeado com confiança nesta revisão** | [PENDENTE DE MAPEAMENTO]. |

### 2.5 Taxonomia de vereditos — seção 6

| Requisito | Referência | Código | Teste | Status / limitação |
|---|---|---|---|---|
| Taxonomia e semântica dos vereditos correspondem à especificação | §6 | `src/ayorai_attractor/verification/judge.py`; `src/ayorai_attractor/evidence/core.py` | `tests/test_verification_judge.py`; **sem teste dedicado de conformidade integral à taxonomia** | [PARCIAL]; reconciliar rótulos e regras com a especificação-fonte. |
| Cobertura parcial não é confundida com suporte integral | §6; futura ADR-009 | Judge e lógica de cobertura, a confirmar | **sem teste de cobertura integral identificado** | [NÃO IMPLEMENTADO — ADR-009]; registrar explicitamente a lacuna. |
| Abstenção e insuficiência são tratadas sem inflar o veredito | §6 | Judge e pipeline de claims | `tests/test_verification_judge.py`; `tests/verification/test_claim_pipeline.py` | [PARCIAL]; limitado aos casos cobertos. |

### 2.6 Benchmark PT-BR — seção 7

| Requisito | Referência | Código / artefato | Teste / evidência | Status | Limitação |
|---|---|---|---|---|---|
| Números e datas são normalizados de modo determinístico | §7 | `src/ayorai_attractor/verification/numeric.py`; `stance.py` e `pt_normalize.py`, se aplicáveis | `tests/test_verification_numeric.py`; `tests/verification/test_f11_metadata_rules.py` | [DECLARADO; confirmar no commit revisado] | Não atribuir esta regra a `judge.py`; cobertura depende de formatos e casos testados. |
| Regras PT-BR e metadados são cobertos por testes pertinentes | §7 | `src/ayorai_attractor/verification/numeric.py` e normalizadores aplicáveis | `tests/test_verification_numeric.py`; `tests/verification/test_f11_metadata_rules.py` | [PARCIAL] | Não presumir cobertura de todo formato regional. |
| Resultados e métricas são publicados com tamanho, composição e incerteza | §7; `docs/eval/BASELINE-v0.md` | Artefatos e documentação de avaliação | `tests/test_judge_evaluation.py`; `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py` | [LIMITAÇÃO DOCUMENTADA] | n=30 e intervalos de confiança incluem o baseline; evitar afirmações generalizadas. |

## 3. Achados que exigem etapas futuras

1. **ADR-001:** status declarado desatualizado; atualizar somente após decisão do mantenedor. Não editar a ADR nesta PR.
2. **ADR-009:** substituirá futuramente ADR-002 §§1 e 4; ainda não foi redigida. Não antecipar conteúdo ou decisão.
3. **Segunda autoridade de veredito:** `EvidenceStore.status()`, em `src/ayorai_attractor/evidence/core.py`, calcula status próprio. Registrar como risco de arquitetura; sem teste dedicado de exclusividade identificado. Não alterar nesta PR documental.
4. **`content_sha256` — PR 0.9:** reprodutibilidade reportada como pendente. Só encerrar com teste determinístico, execução repetível e evidência vinculada ao commit.
5. **Baseline legado:** `orchestrator.py` + `evidence/core.py` (`EvidenceStore.status`) + `evaluation/golden.py` (`_legacy_prediction`, linhas 156–164). A documentação `docs/eval/BASELINE-v0.md`, linha 85, informa PARTIALLY_SUPPORTED em 30/30 e 13/30 corretos (43,3333%), igual à classe majoritária. Não citar `judge.py` como origem desta predição legada.
6. **Artefatos Golden congelados:** incluir `tests/test_frozen_artifacts.py` e `tests/test_golden_digest.py` na rastreabilidade de integridade, além dos testes específicos de avaliação.
7. **Rótulos de verificação:** o commit `d311619` foi reportado pelo Cláudio como testado localmente com `pytest` (348 passed), 34 caminhos existentes e hashes congelados inalterados. Esta evidência aplica-se somente àquele commit; as correções desta revisão precisam de nova execução e novo SHA antes de usar o rótulo [VERIFICADO por execução local — Cláudio, commit X].

## 4. Manutenção e critérios de aceite

- Atualizar esta matriz junto com a alteração do requisito correspondente.
- Usar somente caminhos reais; vincular cada afirmação ao teste realmente pertinente.
- Se não houver teste, escrever “sem teste identificado”; não transformar ausência de evidência em aprovação.
- Toda linha [VERIFICADO] precisa indicar comando, check-run, commit/SHA ou fonte consultada e delimitar exatamente o que foi verificado.
- Preservar Golden, corpus, manifestos, hashes e resultados históricos.
- Conferir a renderização de todas as tabelas no GitHub: cada linha deve ter o mesmo número de células do cabeçalho.
- A PR #120 não deve ser mesclada antes da revisão do conteúdo corrigido e da reverificação local pelo Cláudio, mesmo que os checks de CI estejam verdes.

## 5. Fonte complementar — não canônica

**Estado:** referência complementar; status e autoridade ainda aguardam confirmação do mantenedor. Nenhuma linha da matriz principal depende deste documento.

Rótulos e conceitos anteriormente associados ao “Prompt Mestre v3”, incluindo §3/L0–L14, GEPA, OWASP ASI, Studio, BM25+kNN+RRF e demais itens desse documento, ficam isolados nesta seção. Não são fonte normativa da matriz canônica `AYORAI-ATTRACTOR-BAL` v1.0.0 e não devem ser usados para declarar conformidade com ela. Caso o mantenedor confirme sua relevância, registrar sua identidade, versão e relação com a especificação canônica antes de reintegrar qualquer requisito.
