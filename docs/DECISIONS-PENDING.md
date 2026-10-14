# Pending Decisions

This file records decisions that require explicit maintainer approval. It is a queue, not an approval record. No item below authorizes implementation or changes to an accepted ADR by itself.

Owner and final decision-maker: Anderson Leon Ayora  
Independent reviewer: revisor independente  
Source: execution plan v5, work queue

## Decisões aprovadas

### DEC-005 — r1-a: entrada inválida retorna 500

- **Data da decisão:** 11/10/2026
- **Decisor:** Anderson Leon Ayora
- **Opção aprovada:** A
- **Alternativa não escolhida:** B — manter 500 em r1-a e corrigir só em r2-a; rejeitada porque um 500 nunca foi contrato e um sistema de auditoria não pode falhar com entrada do usuário.
- **Decisão:** Converter falhas de validação de entrada que hoje escapam como `ValueError` do Judge em respostas HTTP 422 estruturadas na v0.4.0, documentando a correção no CHANGELOG.
- **Escopo conhecido:** IDs de evidência duplicados, referências a evidências inexistentes, stances duplicadas, IDs de claim duplicados e stances que apontem para claims inexistentes. Cada categoria deve ter teste específico e formato de erro compatível com o FastAPI.
- **Sequenciamento obrigatório:** Implementar em PR própria após a PR do ResponsePolicy. A PR de baseline #132 permanece como fotografia histórica; a alteração posterior da fixture só poderá mover os três casos de `known_defects` para `invalid_requests` e registrar os corpos 422 esperados, junto com a correção correspondente.
- **Limites:** Não alterar a fixture baseline na PR do ResponsePolicy. Não alterar goldens, corpus, manifestos ou hashes congelados. Não permitir que entradas do schema r1-a produzam HTTP 500.
- **Evidência inicial:** PR #132 congelou os três comportamentos atuais de HTTP 500 antes da mudança de código: https://github.com/Ayorinha/ayorai-opensearch/pull/132
- **Status de implementação:** Aprovada; implementação pendente em PR separada após ResponsePolicy.

### DEC-006 — Prioridade do motor de stance em português (ADR-008)

- **Data da proposta:** 11/10/2026
- **Bloqueia:** nada da Onda 1–2
- **Status:** Pending maintainer decision
- **Decision area:** Benchmark em português e priorização técnica
- **Question:** Priorizar o motor de stance em português (ADR-008) logo após a Onda 2, avaliando-o no `pt-cp-audit` e em um futuro benchmark Anatel?
- **Contexto:** A hipótese é que a detecção de stance — apoia, contradiz ou neutro — em português jurídico seja um gargalo relevante de desempenho. A hipótese deve ser medida, não apresentada como resultado já demonstrado.
- **Opções:**
  - **A — recomendada tecnicamente:** priorizar o motor de stance como primeira prioridade técnica após o Judge 2.0, com avaliação no `pt-cp-audit` e, quando definido, no benchmark de domínio Anatel.
  - **B:** adiar essa prioridade para depois da Fase 3.
- **Recomendação técnica:** A, sujeita à decisão explícita do mantenedor e a métricas estratificadas com tamanho amostral e IC 95%.
- **Impacto a avaliar:** desempenho por tipo de afirmação, qualidade do rótulo de referência, cobertura do português jurídico e risco de generalização indevida.
- **Regra de escopo:** esta proposta não amplia a Onda 1–2, não altera a ordem atual das ondas e não autoriza interpretação jurídica pelo Judge.

## DEC-001 — F3.5: uv lockfile and Docker image digests

- **Data:** 11/10/2026
- **Bloqueia:** F3.5
- **Recomendação técnica:** Adotar `uv.lock` e fixar imagens-base Docker por digest, com procedimento documentado de atualização de segurança. O repositório já contém `docker/Dockerfile` e `docker-compose.yml`, mas não contém `uv.lock`; portanto, a decisão deve cobrir tanto a reprodução das dependências Python quanto a identidade das imagens.

- **Status:** Pending maintainer decision
- **Decision area:** Reproducible builds and software supply-chain controls
- **Question:** Should the project adopt a committed `uv.lock` and pin Docker base images by immutable digest?
- **Context:** A lockfile and image digests can improve repeatability and auditability, but introduce explicit update and maintenance work. A digest pin must be paired with a documented update process.
- **Options to evaluate:**
  1. Adopt both the `uv` lockfile and digest-pinned Docker base images.
  2. Adopt the lockfile first and defer Docker digest pinning.
  3. Defer both until the reproducibility workflow and maintenance policy are specified.
- **Impact to assess:** Developer setup, CI, container builds, security updates, reproducibility instructions, and dependency-update cadence.
- **Approval gate:** Anderson selects an option; revisor independente reviews the implementation proposal before any implementation PR.

## DEC-002 — F4.2: licensing and provenance of source material

- **Data:** 11/10/2026
- **Bloqueia:** F4.2 e a coleta de dados da Fase 4
- **Recomendação técnica:** Exigir licença ou permissão verificável, proveniência e condições de uso registradas para cada fonte destinada a fixtures distribuíveis; excluir do conjunto público o material com direitos não esclarecidos. Isso reduz o risco de redistribuição indevida e mantém auditável a origem dos dados. Como base legal a registrar, a Lei nº 9.610/1998, art. 8º, IV, exclui da proteção autoral os textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais. Fonte primária: https://www.planalto.gov.br/ccivil_03/leis/l9610.htm. Essa exclusão não dispensa registrar URL, órgão, data de publicação, data de coleta e hash do material. Comentários doutrinários, livros e bases privadas permanecem sujeitos à política de bloqueio da DEC-002; não presumir permissão para redistribuí-los.

- **Status:** **Decided on 2026-10-13 — options 1 and 3 combined.** The approved policy is recorded in [DECISIONS-APPROVED.md](DECISIONS-APPROVED.md#dec-002--política-de-licença-e-proveniência-das-fontes). The text below is kept as the historical decision request.
- **Decision area:** Source licensing, permissions, provenance, and evaluation-data governance
- **Question:** What acceptance policy must each external source satisfy before its material is included in evaluation fixtures, examples, or distributable datasets?
- **Context:** Source attribution alone does not establish permission to redistribute content. Each source may have different copyright, license, terms-of-use, privacy, and retention constraints.
- **Options to evaluate:**
  1. Require a recorded license or explicit permission and provenance metadata for every source; exclude sources with unresolved redistribution rights.
  2. Permit documented exceptions for material used only as non-distributed test input, subject to legal and policy review.
  3. Separate public distributable fixtures from privately held evaluation material, with distinct controls and manifests.
- **Impact to assess:** Redistribution rights, benchmark reproducibility, privacy, provenance fields, CI enforcement, and maintenance of source manifests.
- **Approval gate:** Anderson approves the policy after reviewing the legal and technical implications; no source is presumed licensed by this entry.

## DEC-003 — M1: ADR-001 status transition to Accepted

- **Data:** 11/10/2026
- **Bloqueia:** M1
- **Recomendação técnica:** Manter o status atual de ADR-001 até confirmar que decisão, consequências, implementação e testes correspondem ao texto. Só mudar para `Accepted` após revisão explícita do mantenedor e conferência de rastreabilidade pelo revisor independente; não inferir aceitação a partir de implementação parcial.

- **Status:** Pending maintainer decision
- **Decision area:** Architecture decision governance
- **Question:** Is ADR-001 accurate and sufficiently implemented to change its status to `Accepted`, or must its scope and evidence be revised first?
- **Context:** A status label must reflect an explicit decision and the implementation/evidence actually available. This queue entry does not alter ADR-001 or presume acceptance.
- **Options to evaluate:**
  1. Mark ADR-001 `Accepted` after confirming its decision, scope, consequences, and supporting evidence.
  2. Keep its current status and revise the ADR or implementation evidence before reconsideration.
  3. Supersede it with a new ADR if the original decision is no longer appropriate, preserving historical traceability.
- **Impact to assess:** Architectural consistency, traceability, links from implementation and tests, and the audit history of decisions.
- **Approval gate:** Anderson explicitly approves the status change; revisor independente checks the exact ADR diff and its references.

## DEC-004 — M3: commercial documentation and repository name

- **Data:** 11/10/2026
- **Bloqueia:** M3 e partes da Fase 7
- **Recomendação técnica:** Manter `ayorai-opensearch` enquanto se atualiza a documentação comercial com afirmações limitadas às capacidades e avaliações verificadas. Adiar renomeação até existir decisão de posicionamento e plano para links, badges e referências externas, reduzindo quebra desnecessária de URLs.

- **Status:** Pending maintainer decision
- **Decision area:** Public positioning, product documentation, and repository identity
- **Question:** Which commercial-facing documentation is appropriate now, and should the repository name remain `ayorai-opensearch` or be changed?
- **Context:** Commercial material must accurately describe verified capabilities, limitations, evaluation results, licensing, and maturity. Repository renaming affects URLs, badges, integrations, documentation links, and external references.
- **Options to evaluate:**
  1. Keep `ayorai-opensearch` and update commercial documentation without implying capabilities not demonstrated by tests.
  2. Approve a new repository name and coordinate redirects, references, badges, and documentation in a dedicated change.
  3. Defer the naming decision and publish only technical documentation until positioning is approved.
- **Impact to assess:** Public discoverability, continuity of repository links, brand consistency, technical accuracy, and maintenance burden.
- **Approval gate:** Anderson decides the name and positioning; revisor independente reviews factual claims and the documentation diff before publication.


## DEC-007 — Vocabulário de rótulos do benchmark RGC

- **Data da proposta:** 14/10/2026
- **Bloqueia:** congelamento do protocolo e início da anotação do benchmark RGC
- **Status:** Pendente (Anderson)
- **Questão:** O benchmark deve usar os cinco estados produzidos pelo Judge 2.0 ou os seis estados do Golden v0.1?
- **Contexto:** O executor proposto documenta o vocabulário `judge2` (cinco estados) e também disponibiliza `adr002` (seis estados). O protocolo `docs/eval/PROTOCOL-GOLDEN-V1.md` diz para reutilizar os rótulos do Golden v0.1, enquanto o contrato do Judge 2.0 e a ADR-009 definem o conjunto produzido pelo sistema. A escolha afeta o mapeamento de previsões, a matriz de confusão e as métricas.
- **Opções:**
  1. Usar os cinco estados do Judge 2.0 e documentar explicitamente qualquer mapeamento necessário dos rótulos de referência.
  2. Usar os seis estados do Golden v0.1 e definir uma regra prévia e determinística para estados que o Judge 2.0 não produz diretamente.
- **Recomendação técnica:** Opção 1 — usar os cinco estados que o sistema efetivamente produz, evitando criar um contrato de previsão fictício. Antes da anotação, alinhar o protocolo com a ADR-009 e documentar como os estados de referência serão mapeados, excluídos ou tratados sem conversão silenciosa. Golden v0 e Golden v0.1 devem continuar identificados separadamente quando citados; não presumir equivalência entre seus rótulos.
- **Referências:** `docs/eval/PROTOCOL-GOLDEN-V1.md`; ADR-009 — contrato determinístico de adjudicação.
- **Decisão:** pendente (Anderson).

## DEC-008 — Autoria dos casos do benchmark RGC

- **Data da proposta:** 14/10/2026
- **Bloqueia:** definição do fluxo de autoria antes da redação dos casos
- **Status:** Pendente (Anderson)
- **Questão:** Quem redige os aproximadamente 300 casos do benchmark PT-BR?
- **Contexto:** O protocolo atual atribui ao autor a redação de cada caso, incluindo afirmação, trecho da fonte, rótulo e justificativa. O uso de rascunhos assistidos por IA pode reduzir o esforço inicial, mas altera a autoria material e exige rastreabilidade por caso; o sistema avaliado não pode gerar nem alterar os rótulos de referência.
- **Opções:**
  1. **A — autoria integral do autor:** Anderson redige todos os casos conforme o protocolo atual.
  2. **B — rascunhos assistidos:** Claude propõe rascunhos; Anderson aprova ou edita cada caso. Cada registro deve identificar explicitamente quem redigiu o rascunho, quem revisou/editou, quem atribuiu o rótulo e quem aprovou a versão final.
- **Recomendação técnica:** Opção A é a mais simples para preservar o protocolo existente e evitar ambiguidade de autoria. Se Anderson escolher B, emendar o protocolo antes de redigir casos, definir campos de proveniência por caso e manter a decisão humana final sobre afirmação, trecho, rótulo e justificativa.
- **Exigência para o relatório final:** declarar expressamente a opção escolhida. Se B for escolhida, informar a proporção de casos inicialmente redigidos pelo Claude e a proporção revisada/editada/aprovada por Anderson, com trilha de auditoria por caso.
- **Decisão:** pendente (Anderson).

## Queue rules

- These are pending decisions, not accepted architecture or authorization to implement.
- Record the selected option, rationale, date, and approving maintainer before changing an item to decided.
- Keep implementation in a separate PR unless the maintainer explicitly approves a documentation-only decision record.
- Do not claim legal clearance, production readiness, or performance beyond the evidence actually available.
