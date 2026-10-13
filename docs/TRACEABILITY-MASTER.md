# TRACEABILITY MASTER — AYORAI ATTRACTOR

**Estado:** [PROPOSTO] matriz documental em revisão; não autoriza, por si só, declaração de implementação.
**Especificação canônica:** *AYORAI ATTRACTOR — ESPECIFICAÇÃO MESTRA DO LABORATÓRIO BRASILEIRO DE AUDITORIA, BENCHMARK E RASTREABILIDADE DE INTELIGÊNCIA ARTIFICIAL*; identificador `AYORAI-ATTRACTOR-BAL`; versão `1.0.0`.
**Origem da especificação:** documento-fonte fornecido pelo mantenedor; ainda não versionado neste repositório. Proposta futura: versionar em `docs/spec/`, mediante decisão do mantenedor.
**Base da PR:** `main` após PR #119, commit `c4dc36162d8231d78535d1ca1cb00bfdefb9fd4c`.
**Escopo:** somente documentação. Não alterar código, testes, fixtures, Golden, corpus, manifestos ou hashes congelados.

## Decisões de escopo

As decisões abaixo são limites aprovados pelo mantenedor para o domínio técnico e não declaram capacidade já implementada.

- **D10 — Foco de domínio:** a entrada do domínio jurídico será pela regulação de telecomunicações da Anatel, com referência ao Regulamento Geral de Direitos do Consumidor de Serviços de Telecomunicações (RGC), aprovado pela Resolução Anatel nº 765/2023. Não incluir TCU, CGU, Diário Oficial da União ou jurisprudência no escopo técnico nem como promessa no pacote institucional. Fonte primária da resolução: https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1900-resolucao-765%29.
- **D11 — Limite do Judge:** o Judge não interpreta normas, não decide hierarquia normativa nem revogação. O escopo futuro pode representar deterministicamente a referência estrutural (artigo, inciso, parágrafo e alínea) e a data de vigência como metadado/âncora temporal, incluindo o estado `G2 MISSING_TEMPORAL_ANCHOR`; isso não constitui interpretação jurídica.
- **D12 — Terminologia:** manter as formulações já existentes no README: **“LLM ≠ Judge”** e **“Intelligence ≠ Authorization ≠ Execution”**. Ambas já pertencem à terminologia do projeto; não atribuí-las a terceiros. Não introduzir slogans novos sem decisão do mantenedor.
- **Regra de evidência jurídica:** toda referência legal deve apontar para fonte primária conferida. Para a LGPD, art. 20, usar a formulação “direito de solicitar a revisão de decisões tomadas unicamente com base em tratamento automatizado”; não afirmar que a lei exige revisão humana. Fonte primária: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm.
- **Base autoral para material normativo:** Lei nº 9.610/1998, art. 8º, IV: https://www.planalto.gov.br/ccivil_03/leis/l9610.htm. Manter proveniência e metadados de coleta mesmo quando o texto normativo não for protegido por direito autoral.

## Regras de classificação e evidência

- **[VERIFICADO por execução local, commit `d311619`]** significa que o comando foi executado localmente sobre aquele commit. O relato disponível registra `pytest: 348 passed`, os 34 caminhos citados existentes na árvore e os hashes congelados inalterados. Isso **não** valida automaticamente o conteúdo desta revisão nem transfere a verificação para um commit posterior.
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
| 10 | A decisão pode ser reproduzida com os mesmos artefatos e as mesmas regras? | `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py`; `src/ayorai_attractor/evaluation/digest.py` | `tests/test_replay.py`; `tests/test_replay_store.py`; `tests/test_golden_digest.py` | [IMPLEMENTADO — digest semântico v1]; repetição em processo e subprocesso testada; isso não certifica, por si só, todos os caminhos de replay ponta a ponta. |
| 11 | A proveniência dos documentos pode ser verificada? | `src/ayorai_attractor/evidence/`; `src/ayorai_attractor/replay_store.py` | Testes de evidência e replay pertinentes; confirmar cobertura específica | [PARCIAL]; não presumir proveniência integral só porque existe um bundle. |
| 12 | A execução respeitou as restrições de privacidade configuradas? | `src/ayorai_attractor/observability/`; configuração de privacidade a localizar | **sem teste específico de cumprimento das restrições de privacidade identificado** | [SEM TESTE IDENTIFICADO]; não afirmar conformidade LGPD ou ausência de vazamento sem evidência específica. |
| 13 | Alterações no código, nos dados ou nas regras modificaram o resultado? | Replay, avaliação Golden e digests | `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py`; testes de replay pertinentes | [PARCIAL]; integridade de artefatos não demonstra, sozinha, sensibilidade a toda mudança de código/regra. |
| 14 | O sistema é vulnerável a instruções maliciosas inseridas em documentos? | `src/ayorai_attractor/verification/security.py` | `tests/test_verification_response_security.py` | [DECLARADO]; testar no commit revisado; testes específicos não provam imunidade geral a prompt injection. |
| 15 | Um terceiro consegue reconstruir a justificativa técnica do veredito? | Judge, evidências, clusters, ReplayStore e digest semântico | tests/test_verification_judge.py; tests/test_replay.py; tests/test_replay_store.py; tests/test_golden_digest.py | [PARCIAL]; a integridade de digests e os testes de replay apoiam a auditoria, mas ainda não há teste único de reconstrução independente end-to-end. |
| 16 | O sistema consegue identificar quando a informação disponível é insuficiente? | Judge e pipeline de claims | `tests/test_verification_judge.py`; `tests/verification/test_claim_pipeline.py` | [PARCIAL]; distinguir insuficiência explícita de ausência acidental de dados. |
| 17 | O resultado depende excessivamente de um modelo ou fornecedor específico? | Adaptadores de modelos/provedores e avaliação comparativa | **sem teste específico de dependência de fornecedor identificado** | [SEM TESTE IDENTIFICADO]; exige avaliação cruzada com modelos/provedores e protocolo comparável. |
| 18 | É possível identificar em qual etapa ocorreu uma falha? | Orquestração, pipeline, logs e observabilidade | **sem teste de diagnóstico por etapa identificado** | [NÃO IMPLEMENTADO / NÃO COMPROVADO]; confirmar a implementação antes de alterar o rótulo. |
| 19 | O sistema apresenta desempenho consistente em diferentes categorias de casos? | `src/ayorai_attractor/evaluation/golden.py`; conjuntos de avaliação | Testes de avaliação existentes; **sem evidência de cobertura representativa de todas as categorias** | [PARCIAL]; publicar resultados por categoria, tamanho e composição do conjunto. |
| 20 | As conclusões estatísticas são sustentadas pelo tamanho e pela composição do conjunto avaliado? | `docs/eval/BASELINE-v0.md`; protocolo Golden | `tests/test_judge_evaluation.py`; `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py` | [LIMITAÇÃO DOCUMENTADA]; n=30; intervalos de confiança incluem o baseline. Não generalizar além do conjunto avaliado. |

## Componentes de engenharia R1–R20

O registro histórico de componentes R1–R20, com descrições de escopo e links para os runs históricos preservados, está em [docs/history/PROGRESS-2026-10-03.md](history/PROGRESS-2026-10-03.md). Esse arquivo é registro histórico e não declara o estado atual; a matriz abaixo continua sendo a fonte canônica para o estado atual, evidências e limitações.

## 2. Matriz principal de rastreabilidade da especificação canônica

### 2.1 Princípios fundamentais — seção 2

| Requisito | Referência canônica | Código | Teste | Evidência / status | Limitação |
|---|---|---|---|---|---|
| LLM não é autoridade final do veredito | §2.1 — LLM ≠ Judge | src/ayorai_attractor/verification/judge.py; src/ayorai_attractor/evidence/core.py | tests/test_verification_judge.py; tests/test_verdict_authority.py | [PARCIAL — guardas estáticas F1.4 na PR #144, merge 974a3c65d55309a45796b0a59a51177faa3a69da]; os testes AST restringem a construção/acesso indevido a Verdict e imports dinâmicos/de rede no Judge. | A guarda estática reduz vias de autoridade paralela, mas não prova todos os comportamentos runtime nem equivale à implementação do Judge 2.0. |
| Evidência precede conclusão | §2.2 | `src/ayorai_attractor/verification/claim_pipeline.py`; módulos de evidência | `tests/verification/test_claim_pipeline.py` e testes pertinentes de evidência | [PARCIAL]; confirmar relação explícita entre cada conclusão e evidência | A existência de pipeline não prova suporte integral de cada claim. |
| Proveniência integral | §2.3 | `src/ayorai_attractor/evidence/`; `src/ayorai_attractor/replay.py`; `src/ayorai_attractor/replay_store.py`; `src/ayorai_attractor/evaluation/digest.py` | Testes de evidência/replay; `tests/test_golden_digest.py` | [PARCIAL]; `semantic_sha256` v1 é determinístico para o relatório semântico nos testes; proveniência integral e replay ponta a ponta continuam exigindo validação própria. |
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
| Baseline legado corretamente contextualizado | §4; `docs/eval/BASELINE-v0.md`, linha 85 | na tag histórica `baseline-legacy-v0`, `orchestrator.py` e `evidence/core.py` (`EvidenceStore.status`) geravam a predição legada; `evaluation/golden.py` contém o comparador histórico | `tests/test_judge_evaluation.py` | [DECLARADO NA DOCUMENTAÇÃO DO BASELINE]; 13/30 = 43,3333%; PARTIALLY_SUPPORTED em 30/30 | Igual à classe majoritária; não representa evidência de capacidade geral de verificação. |
| Tamanho e composição sustentam as conclusões estatísticas | §4; §7 | `docs/eval/BASELINE-v0.md`; artefatos de avaliação | `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py` | [LIMITAÇÃO DOCUMENTADA] | n=30; intervalos de confiança incluem o baseline; conclusões devem permanecer restritas. |

### 2.4 Arquitetura — seção 5 (itens 5.1 a 5.8)

| Requisito / etapa | Referência | Código candidato | Teste candidato | Status / limitação |
|---|---|---|---|---|
| 5.1 Entrada e validação: identificador único, idioma, afirmação, documentos, metadados, classificação de privacidade e versão do protocolo; rejeitar entradas inválidas com mensagem explícita | §5.1 | `src/ayorai_attractor/verification/models.py` (Pydantic strict); `api_models.py` | `tests/test_verification_models.py` | [PARCIAL]; o Judge atualmente lança `ValueError` em vez de devolver resultado estruturado. |
| 5.2 Normalização: normalizar números e datas de modo determinístico, preservar texto original e registrar transformações | §5.2 | `src/ayorai_attractor/verification/pt_normalize.py`; `numeric.py` | `tests/test_verification_numeric.py`; **sem teste identificado para registro das transformações** | [PARCIAL]; os testes de normalização numérica não demonstram, por si só, que toda transformação é registrada nem cobrem necessariamente todos os formatos de data/número. |
| 5.3 Afirmações atômicas: separar proposições e avaliá-las individualmente | §5.3; ADR-004; ADR-009 futuro | `src/ayorai_attractor/verification/claim_pipeline.py` | `tests/verification/test_claim_pipeline.py` | [PARCIAL]; não há decomposição atômica com cobertura integral; vincular a lacuna à futura ADR-009. |
| 5.4 Recuperação: registrar consulta, filtros, resultados e configuração; distinguir falha de recuperação, extração, proveniência, avaliação de evidência, Judge e relatório | §5.4 | `src/ayorai_attractor/providers/opensearch.py`; `http_search.py`; `mock.py`; `hybrid.py` | `tests/test_opensearch_provider.py`; `tests/test_providers.py`; `tests/test_hybrid.py` | [PARCIAL]; diagnóstico e distinção de falhas por etapa relacionados à pergunta 18: [NÃO IMPLEMENTADO / NÃO COMPROVADO]. |
| 5.5 Evidências: documento, trecho identificável, hashes, posições, método de extração, relação com a afirmação e data de coleta | §5.5 | `src/ayorai_attractor/verification/models.py` (Evidence: offsets, retrieved_at, normalized_content_hash); `extraction.py`; `excerpt.py` | `tests/verification/test_excerpt_revalidation.py` | [PARCIAL]; confirmar cobertura de todos os campos e de sua persistência/proveniência. |
| 5.6 Proveniência: fontes primárias, republicações e origem comum; URLs diferentes não provam independência | §5.6; ADR-006 | `src/ayorai_attractor/verification/clusters.py`; `src/ayorai_attractor/evidence/graph.py` | `tests/test_verification_clusters.py`; `tests/verification/test_f11_metadata_rules.py`; `tests/test_evidence_graph_properties.py` | [PARCIAL]; a independência inferida depende de metadados e relações efetivamente disponíveis. |
| 5.7 Judge determinístico: regras formais, versionadas e testadas; registrar condições satisfeitas/não satisfeitas e motivo | §5.7; ADR-002 | src/ayorai_attractor/verification/judge.py | tests/test_verification_judge.py; tests/test_verdict_authority.py | [PARCIAL]; a autoridade factual permanece no Judge determinístico e as guardas F1.4 limitam caminhos alternativos de construção de Verdict. O contrato atual ainda não registra rule_id, versão das regras e trilha de regras satisfeitas/não satisfeitas; isso pertence ao backlog do Judge 2.0. |
| 5.8 Relatórios: gerar a partir de registros estruturados validados, em formato legível por máquina e documentado por esquema | §5.8 | `src/ayorai_attractor/evaluation/golden.py`; `src/ayorai_attractor/evaluation/digest.py`; `src/ayorai_attractor/replay.py` | `tests/test_golden_digest.py`; testes de avaliação/replay pertinentes; **sem teste de conformidade a JSON Schema versionado** | [PARCIAL — digest semântico v1 IMPLEMENTADO e testado; esquema JSON Schema versionado NÃO IMPLEMENTADO] | `content_sha256` legado mantém a semântica anterior e pode variar por incluir latências aninhadas. O digest semântico não substitui esquema nem prova replay completo. |

**Nota de escopo:** replay e integridade não constituem um item separado da arquitetura §5. Rastreá-los na pergunta 10 (reprodutibilidade) e na §2.3 (proveniência integral), sem rotulá-los como §5.4.

### 2.5 Taxonomia de vereditos — seção 6

| Requisito | Referência | Código | Teste | Status / limitação |
|---|---|---|---|---|
| Taxonomia e semântica dos vereditos correspondem à especificação | §6 | `src/ayorai_attractor/verification/judge.py`; `src/ayorai_attractor/evidence/core.py` | `tests/test_verification_judge.py`; **sem teste dedicado de conformidade integral à taxonomia** | [PARCIAL]; reconciliar rótulos e regras com a especificação-fonte. |
| Cobertura parcial não é confundida com suporte integral | §6; futura ADR-009 | Judge e lógica de cobertura, a confirmar | **sem teste de cobertura integral identificado** | [NÃO IMPLEMENTADO — ADR-009]; registrar explicitamente a lacuna. |
| Abstenção e insuficiência são tratadas sem inflar o veredito | §6 | Judge e pipeline de claims | `tests/test_verification_judge.py`; `tests/verification/test_claim_pipeline.py` | [PARCIAL]; limitado aos casos cobertos. |

### 2.6 Benchmark PT-BR — seção 7

| Requisito | Referência canônica | Artefato / evidência | Status | Limitação |
|---|---|---|---|---|
| Benchmark `ATTRACTOR-PTBR-BENCH` versão `0.1.0` disponível no repositório | §7 | `evals/`; `docs/eval/`; corpus e Golden existentes | [NÃO IMPLEMENTADO] | O corpus atual contém 52 documentos sintéticos en-US; ainda não existe Golden v1 em português. |
| Vinte categorias de casos com critérios, exemplos e métricas | §7.1 | Golden v0 e artefatos de avaliação | [NÃO IMPLEMENTADO] | As categorias atualmente identificadas cobrem apenas parte do escopo, incluindo `factual`, `multi-hop`, `injection` e `independence-*`; não equivalem às 20 categorias especificadas. |
| Piloto com 50 a 100 casos documentados | §7.2 | Golden atual | [NÃO IMPLEMENTADO] | O conjunto atual contém 34 casos, abaixo da faixa de 50–100. |
| Fontes com origem, licença, finalidade e data registradas | §7.3 | Corpus atual | [NÃO IMPLEMENTADO para documentos reais] | O corpus atual é sintético; não constitui o conjunto de fontes reais documentadas previsto pela especificação. |
| Resultados e métricas publicados com tamanho, composição e incerteza | §7; `docs/eval/BASELINE-v0.md` | Artefatos de avaliação; `tests/test_judge_evaluation.py`; `tests/test_frozen_artifacts.py`; `tests/test_golden_digest.py` | [LIMITAÇÃO DOCUMENTADA] | n=30 no baseline avaliado; os intervalos de confiança incluem o baseline. Não generalizar para além dos dados avaliados. |

## Q2 — Módulos sem cobertura medida: limites de escopo

Esta seção registra explicitamente o limite de evidência para módulos identificados na fila Q2. A presença de um módulo no repositório não comprova seu comportamento. Até que exista teste de contrato pertinente e evidência no SHA revisado, os módulos abaixo não devem ser apresentados como controles verificados.

| Módulo | Tratamento atual | Condição para sair deste estado |
|---|---|---|
| `src/ayorai_attractor/cli/main.py` | Teste mínimo de contrato incluído em `tests/test_cli_contract.py` na PR F1.4; comportamento ainda não classificado como verificado até CI no SHA final. | `tests/test_cli_contract.py`: ajuda lista `search`/`eval`, `eval` grava relatório JSON para suite suportada e rejeita suite desconhecida sem gravar saída. | [PENDENTE DE VERIFICAÇÃO]; aguarda suíte completa e check-run verde no SHA exato. |
| `src/ayorai_attractor/memory/core.py` | **Experimental — fora do escopo verificado.** | Adicionar teste mínimo de contrato em PR revisada ou manter explicitamente este limite. |
| `src/ayorai_attractor/observability/audit.py` | **Experimental — fora do escopo verificado.** | Adicionar teste mínimo de contrato em PR revisada ou manter explicitamente este limite. |
| `src/ayorai_attractor/observability/opentelemetry.py` | **Experimental — fora do escopo verificado.** | Adicionar teste mínimo de contrato em PR revisada ou manter explicitamente este limite. |
| `src/ayorai_attractor/providers/catalog.py` | **Experimental — fora do escopo verificado.** | Adicionar teste mínimo de contrato em PR revisada ou manter explicitamente este limite. |
| `src/ayorai_attractor/research_contract.py` | **Experimental — fora do escopo verificado.** | Adicionar teste mínimo de contrato em PR revisada ou manter explicitamente este limite. |
| `src/ayorai_attractor/security/policy.py` | **Experimental — fora do escopo verificado.** | Adicionar teste mínimo de contrato em PR revisada ou manter explicitamente este limite. |

Esta classificação não remove módulos, não altera contratos públicos e não afirma que os módulos são inseguros; apenas impede que sua existência seja confundida com cobertura ou validação. Remoção de qualquer módulo exige decisão nova e registrada. O teste mínimo de contrato de `cli/main.py` foi incorporado em `tests/test_cli_contract.py`; sua classificação só deve mudar para [VERIFICADO] depois da suíte completa e do check-run verde no SHA exato.

## 3. Achados que exigem etapas futuras

1. **ADR-001:** status declarado desatualizado; atualizar somente após decisão do mantenedor. Não editar a ADR nesta PR.
2. **ADR-009:** substituirá futuramente ADR-002 §§1 e 4; ainda não foi redigida. Não antecipar conteúdo ou decisão.
3. **Segunda autoridade de veredito (histórica):** na tag `baseline-legacy-v0`, `EvidenceStore.status()` gerava uma classificação própria. A implementação foi removida pela PR 1.3 (#129); o teste automatizado de exclusividade permanece pendente em F1.4 (PR 1.5).
4. **Digest semântico — PR 0.9:** `semantic_sha256` v1 tem implementação isolada, testes de estabilidade em processo/subprocesso e referências de métricas Golden v0/v0.1. `content_sha256` permanece legado, sem alteração de semântica; sua variação por latência aninhada está documentada.
5. **Baseline legado:** na tag `baseline-legacy-v0`, `orchestrator.py` e `evidence/core.py` (`EvidenceStore.status`) geravam a predição histórica; `evaluation/golden.py` mantém o comparador legado. A documentação `docs/eval/BASELINE-v0.md`, linha 85, informa PARTIALLY_SUPPORTED em 30/30 e 13/30 corretos (43,3333%), igual à classe majoritária. Não citar `judge.py` como origem desta predição legada.
6. **Artefatos Golden congelados:** incluir `tests/test_frozen_artifacts.py` e `tests/test_golden_digest.py` na rastreabilidade de integridade, além dos testes específicos de avaliação.
7. **Rótulos de verificação:** **[VERIFICADO por execução local, commit `1d5d7fa`]** — `pytest -p no:cacheprovider`: 348 passed; nenhum artefato congelado tocado e hashes idênticos; 20/20 perguntas literais conferidas palavra por palavra contra a especificação-fonte; zero linhas de tabela com número de células divergente do cabeçalho. Esta verificação aplica-se somente ao commit `1d5d7fa`; a nova correção ainda precisa ser reverificada e receber seu próprio SHA antes de receber rótulo de verificação.

## 4. Manutenção e critérios de aceite

- Atualizar esta matriz junto com a alteração do requisito correspondente.
- Usar somente caminhos reais; vincular cada afirmação ao teste realmente pertinente.
- Se não houver teste, escrever “sem teste identificado”; não transformar ausência de evidência em aprovação.
- Toda linha [VERIFICADO] precisa indicar comando, check-run, commit/SHA ou fonte consultada e delimitar exatamente o que foi verificado.
- Preservar Golden, corpus, manifestos, hashes e resultados históricos.
- Conferir a renderização de todas as tabelas no GitHub: cada linha deve ter o mesmo número de células do cabeçalho.
- A PR #120 não deve ser mesclada antes da revisão do conteúdo corrigido e da reverificação local, mesmo que os checks de CI estejam verdes.

## 5. Fonte complementar — não canônica

**Estado:** referência complementar; status e autoridade ainda aguardam confirmação do mantenedor. Nenhuma linha da matriz principal depende deste documento.

Rótulos e conceitos anteriormente associados ao plano de execução v3, incluindo §3/L0–L14, GEPA, OWASP ASI, Studio, BM25+kNN+RRF e demais itens desse documento, ficam isolados nesta seção. Não são fonte normativa da matriz canônica `AYORAI-ATTRACTOR-BAL` v1.0.0 e não devem ser usados para declarar conformidade com ela. Caso o mantenedor confirme sua relevância, registrar sua identidade, versão e relação com a especificação canônica antes de reintegrar qualquer requisito.


## PR 1.2a — contrato de não adjudicação [MESCLADA #125]

- Requisito: apenas o Judge determinístico em `/v1/verify` pode produzir o veredito factual.
- API de busca e auditoria: `verification=null`, `verdict_authority=not_adjudicated`, `formal_verification_endpoint=/v1/verify`; falhas operacionais ficam em `operation_status`.
- Orquestrador: não consulta `EvidenceStore.status()` para decidir o veredito e não reaproveita a saída dos agentes como declaração de verificação factual.
- Persistência transitória: enquanto `verification` continuar `NOT NULL`, grava-se `not_adjudicated`; a resposta pública da consulta de auditoria não expõe esse marcador como veredito.
- Testes de contrato atualizados; execução, digests semânticos e hashes de artefatos congelados dependem de verificação independente no SHA exato.
- PR 1.3 remove `VerificationStatus` e `EvidenceStore.status()`; a classificação factual permanece exclusiva do Judge determinístico em `/v1/verify`. Essa remoção não declara a implementação completa do Judge 2.0.0.
- Estado: [MESCLADA #125]; tag `baseline-legacy-v0` confirmada. A revisão independente e o CI da PR 1.3 são gates separados.


## PR 1.2a — contrato sem adjudicação factual [MESCLADA #125]

- O orquestrador preserva a análise produzida pelos agentes, mas a separa do veredito factual;
  `notice` informa que nenhum veredito foi adjudicado e direciona a `/v1/verify`.
- `verification=null`, `verdict_authority=not_adjudicated`; falhas operacionais são expostas em `operation_status`.
- `confidence` é depreciado e retorna `null`; remoção planejada para v0.6.0.
- `r2-v1` identifica eventos históricos com semântica legada; `r2-v2` identifica novos eventos
  `not_adjudicated`. Consultas de auditoria retornam `not_recorded` até a migração de persistência
  da PR 1.2b.
- A regeneração do baseline legado é bloqueada nesta versão e orienta a execução a partir da tag
  histórica; manifesto congelado não é alterado.
- Verificação de testes, lint, tipos, hashes congelados e semantic_sha256: pendente de verificação independente
  no SHA final da PR.

## Fila futura — adendo de domínio jurídico, evidência e citações (11/10/2026)

Esta fila complementa o plano de execução v5. **Não altera a ordem das Ondas 1–3 em andamento.** A sequência ativa permanece: fechar DEC-005 (500 → 422), F1.4, F1.5 e M5, respeitando os gates de revisão independente e CI; M5 já deve aplicar as regras de citação acima.

- **F2.7 — acréscimo:** reportar métricas estratificadas por tipo de afirmação: numérica, data/prazo, remissão legal e conflito de fontes. Publicar `n` por estrato e IC 95%; não inferir desempenho de estratos com amostra insuficiente.
- **F4.2 — acréscimo:** registrar a base legal da Lei nº 9.610/1998, art. 8º, IV, e exigir URL, órgão, data de publicação, data de coleta e hash para cada fonte normativa. Comentários doutrinários, livros e bases privadas continuam bloqueados pela DEC-002.
- **F4.4 — acréscimo:** repetir a estratificação por tipo de afirmação (numérica, data/prazo, remissão legal, conflito de fontes), sempre com IC 95% e `n` explícito por estrato.
- **F4.5 — novo, após F4.3:** parser determinístico de referências normativas em português, cobrindo artigo, inciso, parágrafo, alínea, `caput`, plural `§§`, incisos romanos e referências como “Resolução nº 765/2023”. Produzir forma canônica e testes de propriedade e casos-limite (`º/o`, abreviações e pontuação). Não interpretar conteúdo jurídico, hierarquia, revogação ou vigência; a data de vigência é apenas metadado/âncora temporal.
- **DEC-006:** decisão pendente de priorização do motor de stance em português (ADR-008) após a Onda 2; não bloqueia as Ondas 1–2.



## Onda 2 — Judge 2.0.0 contract identity and pre-adjudication gates

- **Contrato normativo 2.0.0:** `rules/judge-2.0.0.json`; `rules_sha256` canônico registrado: `493cce66ce45fcb432b8345e7567cfb39858492bfe46d5fa6b584991e79e9efc`. O hash é recalculado a partir das regras carregadas; cada `GateResult` registra o digest efetivamente carregado.
- **Base da fundação:** PR #150, SQUASH commit `07e95680a24b5ffcbba903314929c261cdcc4c88`. A identidade do contrato deve permanecer estável; mudanças no documento de regras exigem novo hash e rastreabilidade explícita.
- **Item 2.2 — estado:** [IMPLEMENTAÇÃO EM REVISÃO; NÃO VERIFICADO ATÉ CI VERDE E APROVAÇÃO INDEPENDENTE DO SHA FINAL].
- **G1:** `src/ayorai_attractor/verification/judge2/gates.py`; testes dedicados para os oito códigos em `tests/verification/test_judge2_gates.py`. Os erros reutilizam `InvalidJudgeInput` e resultam em `decision_state=INVALID_INPUT`.
- **G2:** os cinco motivos normativos têm testes dedicados; o resultado é `decision_state=ABSTAINED`, sem veredito factual.
- **E1–E3:** os motivos `SOURCE_UNAVAILABLE`, `OFFSET_INVALID`, `EXCERPT_MISMATCH` e `NEUTRAL_STANCE` são registrados por par evidência/átomo. E2 sempre compara o trecho normalizado em NFC com a fatia da fonte; o hash da fonte inteira é uma verificação adicional. Testes negativos cobrem excerpt fabricado sem hash, deslocamento de um caractere, equivalência NFC/NFD e offsets Unicode por code point em `tests/verification/test_judge2_gates.py`.
- **Relatório de implementação:** `docs/reports/JUDGE-2.0.0-GATES-REPORT.md`.
- **Limite explícito:** a saída do item 2.2 não contém campo `verdict`; o estado `decision_state=null` com `admissible=true` significa apenas que os portões não bloquearam a entrada. Nenhuma adjudicação factual é feita nesta etapa.
- **Integridade:** Goldens, corpus, manifestos, thresholds e hashes congelados não devem ser modificados por este item. A classificação só poderá mudar para [VERIFICADO] após CI verde, revisão independente do SHA exato e conferência do diff.
