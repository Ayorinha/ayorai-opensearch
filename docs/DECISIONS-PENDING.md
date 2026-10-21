# Pending Decisions

This file records decisions that require explicit maintainer approval. It is a queue, not an approval record. No item below authorizes implementation or changes to an accepted ADR by itself.

Owner and final decision-maker: Anderson Leon Ayora  
Independent reviewer: revisor independente  
Source: execution plan v5, work queue

## Índice de decisões (atualizado em 2026-10-21)

Este índice só localiza registros; o texto de cada decisão continua sendo a fonte. **Atenção:** os identificadores DEC-007 e DEC-008 foram usados duas vezes, com significados diferentes. Até decisão do mantenedor sobre renumeração, cite sempre o identificador com o qualificador desta tabela.

| ID | Assunto | Estado | Registro |
|---|---|---|---|
| DEC-001 | `uv.lock` e digests de imagens Docker | Pendente | Este arquivo |
| DEC-002 | Licença e proveniência das fontes | Aprovada (2026-10-13) | [DECISIONS-APPROVED.md](DECISIONS-APPROVED.md#dec-002--política-de-licença-e-proveniência-das-fontes) |
| DEC-003 | ADR-001 → `Accepted` | Pendente | Este arquivo |
| DEC-004 | Documentação comercial e nome do repositório | Pendente | Este arquivo |
| DEC-005 | r1-a: entrada inválida retorna 422 | Aprovada (2026-10-11); implementada na PR #139 (v0.4.0) | Este arquivo |
| DEC-006 | Prioridade do motor de stance em português | Pendente | Este arquivo |
| DEC-007 (release) | Publicar v0.4.0 | Aprovada (2026-10-11) | [DECISIONS-APPROVED.md](DECISIONS-APPROVED.md) |
| DEC-007 (RGC) | Vocabulário de cinco vereditos do RGC | Aprovada (2026-10-15); Emenda 2 mesclada na PR #193 | Este arquivo |
| DEC-008 (release) | Publicar v0.5.0 | Aprovada (2026-10-13) | [DECISIONS-APPROVED.md](DECISIONS-APPROVED.md) |
| DEC-008 (RGC) | Autoria dos casos do RGC | Aprovada (2026-10-15) | Este arquivo |
| DEC-009 | Abstenção avaliada como `UNVERIFIED` | Aprovada (2026-10-15); executor na PR #195 | Este arquivo |
| DEC-010 | Afirmações compostas (opção A) | Aprovada (2026-10-16); executor na PR #203, Emenda 3 na PR #205 | Este arquivo |
| DEC-011 | Guia de anotação após o piloto 01 | Aprovada (2026-10-17); Emenda 4 na PR #227 | Este arquivo |
| DEC-012 | Decisões 1–4 do log de auditoria (ADR-010) | Registro mesclado na PR #225 em 2026-10-17; implementação e validação continuam sujeitas aos gates da ADR-010 | [PR #225](https://github.com/Ayorinha/ayorai-opensearch/pull/225) |
| DEC-013 | Autorização de execução e merge por agente neste ciclo | Aprovada por ordem do mantenedor (2026-10-18); escopo limitado | Este arquivo |
| DEC-014 | Baseline primário e descritivo do RGC | Aprovada por ordem do mantenedor (2026-10-18); Emenda 5 | Este arquivo |
| DEC-015 | Autorização da Etapa 2 (manual técnico) | Aprovada (2026-10-18); escopo documental | Este arquivo |
| DEC-016 | Autorização de trabalho autônomo e ratificação documental | Aprovada por ordem do mantenedor (2026-10-21); limites científicos preservados | Este arquivo |
| DEC-017 | RGC: registro ausente versus INVALID_PREDICTION | Pendente; recomendação A, aguardando decisão explícita do mantenedor | Este arquivo |

## Decisões aprovadas

### DEC-007 — Vocabulário de rótulos do benchmark RGC

- **Data da decisão:** 15/10/2026
- **Decisor:** Anderson Leon Ayora
- **Opção aprovada:** 1 — usar os cinco vereditos do Judge 2.0.
- **Decisão:** O benchmark RGC usa os cinco vereditos definidos em `rules/judge-2.0.0.json` (`enums.verdict`), com a semântica da ADR-009 (K1–K5), e não a semântica da ADR-002. Esta decisão vale somente para o RGC; Golden v0, v0.1 e derivados r2 permanecem inalterados. `VERIFIED` não é rótulo de referência no RGC; corroboração R0–R3 é um eixo separado e não é anotada no v1.
- **Implementação documental:** Emenda 2 em `docs/eval/PROTOCOL-GOLDEN-V1.md`; lista histórica do pré-registro preservada como histórica.
- **Estado:** Aprovada; a implementação documental aguarda revisão e merge pelo mantenedor.
- **Atualização (2026-10-17):** a Emenda 2 foi mesclada na [PR #193](https://github.com/Ayorinha/ayorai-opensearch/pull/193) em 2026-10-15.

### DEC-008 — Autoria dos casos do benchmark RGC

- **Data da decisão:** 15/10/2026
- **Decisor:** Anderson Leon Ayora
- **Opção aprovada:** A — Anderson redige e rotula os aproximadamente 300 casos.
- **Decisão:** Anderson será responsável pela redação e rotulagem dos casos. Mantêm-se a segunda anotação independente, Cohen's kappa ≥ 0,6 e o registro caso a caso das divergências. Enquanto houver um único anotador, o conjunto será identificado como `v1-draft`, e seus resultados não serão usados como resultado principal.
- **Estado:** Aprovada; nenhuma anotação ou execução de benchmark é autorizada por este registro isoladamente.

### DEC-009 — Mapeamento de abstenção na avaliação RGC

- **Data da decisão:** 15/10/2026
- **Decisor:** Anderson Leon Ayora
- **Opção aprovada:** Avaliar `ABSTAINED` do Judge como `UNVERIFIED`.
- **Justificativa:** A abstenção significa que o Judge não encontrou base para decidir; isso equivale ao rótulo de referência `UNVERIFIED`. O relatório deve informar quantas previsões vieram originalmente de `ABSTAINED`, separadamente da contagem do veredito mapeado.
- **Estado:** Aprovada; aplica-se ao executor de avaliação RGC e não altera o contrato de saída do Judge nem os Golden históricos.

### DEC-010 — Afirmações compostas no benchmark RGC

- **Data da decisão:** 16/10/2026
- **Decisor:** Anderson Leon Ayora
- **Opção aprovada:** A — o anotador marca os átomos de cada afirmação composta, com offsets; o executor usa esses átomos para adjudicação.
- **Proporção-alvo:** cerca de um terço dos casos definitivos será composto; a proporção efetiva deverá constar no relatório.
- **Decisão:** a unidade de anotação e execução para afirmações compostas será formalizada pela Emenda 3 de `docs/eval/PROTOCOL-GOLDEN-V1.md` e refletida no pré-registro. A implementação de código foi mesclada na [PR #203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) em 2026-10-16: campo `atoms` nos casos e executor `rgc-eval/0.2.0`; casos sem `atoms` mantêm o mesmo `output_sha256`.
- **Opções consideradas (texto preservado):**
  - **A — escolhida:** o anotador marca as partes (átomos) de cada afirmação composta, incluindo offsets; o executor usa esses átomos para adjudicação. O formato e a regra entram em uma emenda ao protocolo e no pré-registro antes da anotação definitiva. A opção preserva a semântica da Emenda 2 e permite avaliar o Judge com afirmações compostas.
  - **B — não escolhida:** o v1 aceita apenas afirmações atômicas; afirmações compostas ficam para o v2. A ausência de `PARTIALLY_SUPPORTED` no v1 seria declarada explicitamente, com regra para identificar/excluir afirmações compostas.
- **Fato que motivou a decisão:** o executor anterior tratava cada afirmação como um único átomo. Pelas regras A1–A4 de `rules/judge-2.0.0.json`, um átomo pode resultar em `SUPPORTED`, `REFUTED`, `CONFLICTING` ou `UNVERIFIED`; K4 exige dois ou mais átomos para `PARTIALLY_SUPPORTED`. `CONFLICTING` continua possível pela regra A4. Ver [RUNNER-RGC-v1.md §5](eval/RUNNER-RGC-v1.md#5-limitações-conhecidas-declaradas-antes-dos-dados).
- **Estado:** aprovada. O código (PR #203) está mesclado; a emenda ao protocolo segue em PR própria. A mesclagem não equivale à validação do executor no benchmark definitivo.
- **Atualização (2026-10-17):** a Emenda 3 foi mesclada na [PR #205](https://github.com/Ayorinha/ayorai-opensearch/pull/205) em 2026-10-16.

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
- **Atualização (2026-10-17):** implementada na [PR #139](https://github.com/Ayorinha/ayorai-opensearch/pull/139), mesclada em 2026-10-11 e publicada na v0.4.0 (ver `CHANGELOG.md`).

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
- **Fato verificado (2026-10-17):** a main ainda não contém `uv.lock`, e `docker/Dockerfile` usa a tag móvel `python:3.12-slim`, sem digest. O endurecimento da PR #222 não resolveu esta decisão.

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

## DEC-011 — Guia de anotação do RGC após o piloto (fase 1)

- **Data da proposta:** 16/10/2026
- **Data da aprovação:** 17/10/2026
- **Decisor:** Anderson Leon Ayora
- **Status:** Aprovada; implementação documental e piloto exploratório autorizados conforme os gates abaixo.
- **Bloqueia:** segundo piloto, congelamento do protocolo RGC e redação dos 300 casos definitivos.
- **Origem:** piloto exploratório de 20 casos (fase 1 do [protocolo](eval/PROTOCOL-GOLDEN-V1.md)), rotulado pelo mantenedor em 16/10/2026. Os rótulos do piloto não integram o benchmark e não foram exportados para o repositório. Os achados abaixo se referem aos casos pelo identificador do piloto.
- **Distribuição observada no piloto:** 9 `SUPPORTED`, 11 `REFUTED`, 0 `UNVERIFIED`, 0 `PARTIALLY_SUPPORTED`, 0 `CONFLICTING`, 0 `RULE_GAP`. O piloto não continha caso projetado para `PARTIALLY_SUPPORTED` ou `CONFLICTING`; essas regras ainda não foram exercitadas por um anotador humano.
- **Pergunta:** quais regras de anotação devem ser acrescentadas ao protocolo (Emenda 4) para eliminar as ambiguidades encontradas no piloto?

### Parte 1 — "Não confirma" não é "contradiz"

- **Fato (pilot-18):** a justificativa registrada diz que a afirmação "não encontra respaldo na evidência apresentada", mas o rótulo escolhido foi `REFUTED`. O trecho não menciona multa diária, nem para conceder nem para negar.
- **Regra proposta:**
  1. `REFUTED` exige que algum trecho afirme algo **incompatível** com a afirmação (outro valor, outro sujeito, outra condição, negação expressa).
  2. Se os trechos apenas não tratam do ponto, o rótulo é `UNVERIFIED`, mesmo que o anotador acredite que a afirmação seja falsa.
  3. Teste de controle, escrito no guia: *"Consigo apontar a frase do trecho que diz o contrário?"* Se não, não é `REFUTED`.
  4. A justificativa deve citar a frase incompatível em todo caso `REFUTED`.

### Parte 2 — Retificação e texto superado

- **Fato (pilot-19):** o trecho 1 (texto original do art. 84) confirma a afirmação e o trecho 2 (retificação de 26/12/2023) a contradiz. Pela regra atual ("para a mesma parte, há trecho que confirma e trecho que contradiz"), o rótulo seria `CONFLICTING`; o rótulo dado foi `REFUTED`, que é o resultado juridicamente correto. Nenhuma regra do Judge 2.0 trata precedência temporal ou retificação.
- **Agravante verificado:** o próprio documento de retificação no corpus (`rgc-res-765-2023-retificacao-2023-12-26` em `evals/ptbr/sources/DOCUMENTS.jsonl`) reproduz o texto superado no trecho "Onde se lê", e o corpus contém uma segunda retificação (`rgc-res-765-2023-retificacao-2024-01-12`). No modo `retrieval`, o sistema pode recuperar o texto superado como evidência.
- **Opções:**
  - **A — recomendada tecnicamente para o v1:** regra apenas de anotação. O rótulo de referência segue o **texto vigente** (original com as retificações aplicadas); texto superado ("Onde se lê" ou redação original retificada) não conta como evidência de apoio. O Judge não é alterado. Casos que envolvem dispositivo retificado recebem a marca `rectified: true` e o relatório apresenta o desempenho nesse estrato separadamente, declarando a limitação.
  - **B:** alterar o Judge ou o detector de stance para reconhecer precedência temporal e o marcador "Onde se lê". Exige ADR, nova versão de regras, testes e hashes novos; fica fora do v1.
  - **C:** excluir do v1 todo dispositivo retificado (arts. 84, 86, 34, 90, 93 e 96 da Resolução 765/2023 e do Anexo), com registro no log de exclusões.
- **Recomendação técnica:** A. Mede o sistema como ele é, sem alterar o Judge, e torna a limitação visível em vez de escondê-la. B pode ser proposta para o v2 com base no estrato medido.
- **Escolha do mantenedor (17/10/2026):** opção **A**, aprovada. O rótulo de referência segue o texto vigente após as retificações; redações superadas em “Onde se lê” não contam como apoio. Casos afetados recebem `rectified: true` e são reportados em estrato separado; o Judge permanece inalterado.

### Parte 3 — Valores, quantificadores e modalidade

- **Fatos:** pilot-04 (afirmação "no mínimo 5 anos"; texto "mínimo de 3 anos") e pilot-12 (afirmação "exclusivamente por carta"; texto "preferencialmente por meio eletrônico"). Em pilot-12, a justificativa registrada diz que a afirmação "acrescenta uma restrição que não consta", argumento de ausência, enquanto o rótulo foi `REFUTED`.
- **Regras propostas, com exemplos do piloto:**

  | Situação | Rótulo | Exemplo |
  |---|---|---|
  | A afirmação dá **outro valor** para o mesmo prazo, período, percentual ou data | `REFUTED` | 5 anos vs. "mínimo de 3 anos" (pilot-04); 10 vs. 7 dias (pilot-02); dezembro vs. novembro (pilot-17) |
  | A afirmação diz **"exclusivamente/somente X"** e o texto admite ou prefere outro meio ou condição | `REFUTED` | "exclusivamente por carta" vs. "preferencialmente por meio eletrônico" (pilot-12); "somente em dias úteis" vs. "24 horas, 7 dias" (pilot-08) |
  | A afirmação diz **"exclusivamente/somente X"** e o texto não trata de meio ou condição | `UNVERIFIED` | — |
  | A afirmação diz **"integralmente/totalmente"** e o texto limita o alcance | `REFUTED` | revogação integral vs. revogação de artigos específicos (pilot-19, aplicada a Parte 2) |
  | A afirmação troca **dever por faculdade** (ou o inverso), ou **permissão por proibição** | `REFUTED` | "pode ser cobrado" vs. "sem ônus" (pilot-06); "configura restrição vedada" vs. "não configura" (pilot-09) |
  | A afirmação transforma **"preferencialmente"** em obrigação ("deve ser por meio eletrônico") sem dizer "exclusivamente" | **ponto aberto** | Anderson decide: `REFUTED` (o texto não obriga) ou excluir esse tipo de afirmação do v1 |

- **Decisão do mantenedor (17/10/2026):** tabela aprovada. Afirmações que transformem “preferencialmente” em obrigação sem suporte textual explícito ficam excluídas do v1; não serão rotuladas por inferência interpretativa.

### Encaminhamento proposto após aprovação

1. Registrar as regras aprovadas como **Emenda 4** em `docs/eval/PROTOCOL-GOLDEN-V1.md`, com nota datada no pré-registro.
2. **Segundo piloto** de cerca de 10 casos novos, com pelo menos 3 compostos com parte sem confirmação (`PARTIALLY_SUPPORTED`), 1 com fontes divergentes (`CONFLICTING`), 1 envolvendo dispositivo retificado e 2 de ausência (`UNVERIFIED`). Os casos do segundo piloto também são descartados.
3. Só depois do segundo piloto: congelamento do protocolo e redação dos 300 casos.

- **Isolamento (DEC-008):** os textos do primeiro piloto foram consultados em assistentes externos (Grok, ChatGPT). O mantenedor confirmou (17/10/2026) que a justificativa de pilot-04 foi redigida com auxílio do Grok; os demais rótulos foram dados por ele. Por ser descartado, isso não afeta o benchmark. Para o segundo piloto e para o conjunto definitivo, nenhum caso pode ser enviado a ferramenta de IA antes do congelamento e da execução única.
- **Impacto:** guia de anotação, protocolo, pré-registro e relatório. Não altera código, regras do Judge, hashes ou artefatos Golden.
- **Aprovação registrada (17/10/2026):** Anderson aprovou as três partes: (1) ausência de confirmação = `UNVERIFIED`; `REFUTED` exige contradição explícita e justificativa com citação incompatível; (2) opção A para retificação; (3) tabela de valores, quantificadores e modalidade, excluindo do v1 afirmações que convertam “preferencialmente” em obrigação sem suporte textual explícito.
- **Próximo gate:** executar o segundo piloto com cerca de 10 casos novos, usando apenas fontes oficiais verificadas e anotação humana independente de ferramentas de IA. Os casos do piloto serão descartados e não poderão ser enviados a assistentes/modelos. Após análise dos resultados, solicitar congelamento formal do protocolo antes de redigir os 300 casos definitivos.


## DEC-013 — Autorização de execução e merge por agente (ciclo de 2026-10-18)

- **Data:** 2026-10-18
- **Decisor:** Anderson Leon Ayora, criador e mantenedor do repositório.
- **Escopo:** autoriza, exclusivamente neste ciclo, a execução das ondas e a atualização, abertura, comentário, merge e fechamento das PRs #232, #241, #242, #255 e #257, além das PRs abertas para cumprir a ordem final de execução. A PR #256 foi mesclada neste ciclo e deve ser registrada no status.
- **Revisão:** a revisão humana independente fica dispensada apenas para este ciclo por autorização expressa do mantenedor. O achado F-01 permanece aberto; esta dispensa não deve ser descrita como revisão independente realizada.
- **Limites:** não autoriza alterar tags, releases, configuração do repositório, regras do Judge, Golden, hashes congelados, fontes RGC capturadas, pré-registros nem criar, rotular ou executar casos do benchmark RGC. Permanecem obrigatórios os portões técnicos, checks do SHA final e proteção dos artefatos definidos na ordem do mantenedor.
- **Registro:** a PR #256 foi mesclada neste ciclo. Cada PR mesclada neste ciclo deve conter a linha: “Mesclada sob a autorização DEC-013 do mantenedor; revisão humana independente dispensada neste ciclo (achado F-01 permanece aberto).”
- **Estado:** autorizada pelo mantenedor em 2026-10-18; não equivale a revisão humana independente nem encerra F-01.
- Ausência do campo rectified tratada como false (não retificado), decisão do mantenedor em 2026-10-18, implementada na PR #232.


## DEC-014 — Baseline primário e descritivo do RGC

- **Data:** 2026-10-18
- **Decisor:** Anderson Leon Ayora, mantenedor do repositório.
- **Opção aprovada:** B como baseline primário; A como referência descritiva.
- **Baseline primário B:** fixar a classe majoritária exclusivamente a partir dos rótulos da partição pública de desenvolvimento (70%), registrar a classe antes de qualquer execução no conjunto oculto e aplicá-la sem alteração à avaliação confirmatória. O cálculo não usa os rótulos da partição avaliada para escolher a classe.
- **Baseline descritivo A:** calcular a classe majoritária na própria partição avaliada e reportá-la apenas como “baseline-oráculo descritivo da prevalência observada”. A não é classificador operacional e nunca é usada como base do teste H1.
- **Implementação autorizada:** a simulação de desenho gera partições de desenvolvimento e avaliação com a mesma prevalência populacional, deriva B da partição de desenvolvimento, calcula H1 contra B e reporta A ao lado. Seed 20261003, 10.000 reamostragens de bootstrap e 200 repetições por célula são mantidos. Todos os números da simulação são sintéticos, não resultados do benchmark RGC PT-BR.
- **Limites:** esta decisão e a Emenda 5 não congelam o protocolo, não alteram o pré-registro, não autorizam acessar ou executar casos do benchmark e não mudam o Judge, Golden, manifestos ou hashes congelados.
- **Estado:** aprovada pelo mantenedor nesta ordem em 2026-10-18; Emenda 5 a registra em `docs/eval/PROTOCOL-GOLDEN-V1.md`.
- **Atualização datada (2026-10-21) — Emenda 6:** Anderson aprovou explicitamente a incorporação da definição B/A ao pré-registro. A restrição anterior de que a DEC-014/Emenda 5 “não altera o pré-registro” é superada por esta emenda aprovada, que mantém a redação anterior como histórico e acrescenta a interpretação vigente para H1. O desempate de B segue a ordem fixa do vocabulário `judge2` em `majority_label`. O estado do protocolo permanece **[PROPOSTO]**; não há congelamento nem autorização de execução. Implementação documental proposta na PR da Emenda 6.
- **Atualização datada (2026-10-21):** a implementação documental deixou de ser proposta e foi incorporada pela PR #288 (`5a587ecb64abc6359c8fe36b8194b67dee3edda9`). A baseline B/A está registrada no pré-registro e no protocolo; o estado continua [PROPOSTO] e o congelamento segue dependente do piloto 02 humano e de decisão separada.

## DEC-015 — Autorização da Etapa 2 (manual técnico)

- **Data:** 2026-10-18
- **Decisor:** Anderson Leon Ayora, mantenedor do repositório.
- **Escopo autorizado:** escrever, abrir, atualizar e mesclar PRs exclusivamente de documentação para a Etapa 2 do Manual Técnico, incluindo os Passos 0 a 3 definidos pelo mantenedor. A autorização cobre os arquivos documentais indicados em cada passo e, no Passo 1, a alteração da descrição do pacote e do texto de ajuda da CLI.
- **Revisão:** revisão humana independente dispensada nesta etapa por autorização expressa do mantenedor. O achado F-01 permanece aberto; esta dispensa não deve ser descrita como revisão independente realizada.
- **Regras de evidência:** toda afirmação técnica do manual deve apontar para arquivo, teste, workflow ou SHA. Antes de usar fatos fornecidos pelo mantenedor, confirmar no código da `main`; em caso de divergência, prevalece o código e a diferença deve ser registrada.
- **Processo:** uma PR por passo, criada a partir da `main` atual. Mesclar somente com todos os checks verdes no SHA final; usar squash e mensagem escrita manualmente no formato “<título> (#n)” seguido de uma ou duas linhas. Cada PR mesclada deve registrar: “Mesclada sob a autorização DEC-015 do mantenedor; revisão humana independente dispensada nesta etapa (F-01 permanece aberto).” Se uma branch não puder ser atualizada, recriar a PR a partir da `main` e fechar a anterior apontando para a nova.
- **Falha intermitente específica:** se somente o check “Schemathesis all contract checks” falhar numa PR que não altera código da API, reexecutar o job; se persistir, registrar a ocorrência e seguir.
- **Padrão editorial:** português do Brasil; nomes de campos, rotas e comandos permanecem exatamente como no código. Cada capítulo começa com “Estado: Atual · Referência: main @ <SHA curto> · Atualizado: <AAAA-MM-DD>” e “Fontes de verdade: <arquivos e testes>”, seguido de Propósito → Como funciona → Contratos e parâmetros → Limites conhecidos → Evidências → Ver também. Tom técnico e sóbrio; não usar “garante”, “certificado”, “à prova de adulteração” ou “pronto para produção”; preferir “implementado”, “implementado como biblioteca”, “proposto” e “não implementado”.
- **Exclusões expressas:** não alterar tags, releases, configuração do repositório, regras do Judge, Golden, hashes, fontes RGC, pré-registros, protocolo, OpenAPI ou casos do benchmark. Não alterar comportamento do produto nem arquivos protegidos.
- **Estado:** autorizado pelo mantenedor em 2026-10-18; F-01 continua aberto.

## Queue rules

- These are pending decisions, not accepted architecture or authorization to implement.
- Record the selected option, rationale, date, and approving maintainer before changing an item to decided.
- Keep implementation in a separate PR unless the maintainer explicitly approves a documentation-only decision record.
- Do not claim legal clearance, production readiness, or performance beyond the evidence actually available.


### DEC-016 — Autorização de trabalho autônomo e ratificação documental

- **Data da autorização:** 2026-10-21
- **Decisor:** Anderson Leon Ayora, mantenedor do repositório.
- **Status:** Aprovada por ordem explícita do mantenedor; registrada nesta PR. Esta autorização de processo não congela o protocolo RGC nem decide questões científicas pendentes.
- **Escopo:** autoriza o agente a inspecionar, corrigir, testar, abrir e atualizar PRs, rebasear branches, resolver conflitos, reexecutar checks, mesclar por squash quando os gates definidos forem atendidos e continuar o backlog técnico/documental sem pedir confirmação a cada etapa.
- **Regra para escolhas técnicas/editoriais:** escolher a alternativa conservadora e reversível, registrar a justificativa na PR e prosseguir. Decisões científicas ainda não tomadas pelo mantenedor permanecem pendentes, com opções, prós/contras e recomendação documentados; não devem bloquear tarefas independentes.
- **Gates de merge:** antes de mesclar, exigir rebase na `main` atual, checks obrigatórios verdes no SHA final e evidência de execução de `pytest -q`, `ruff check .`, `ruff format --check .` e `mypy --strict evals/ptbr/rgc_eval.py`. Não declarar comandos executados sem evidência. Se a infraestrutura disponível impedir execução local, registrar a limitação e não afirmar que esse gate foi cumprido.
- **Limites científicos e de integridade:** não congelar o protocolo antes do piloto 02 humano; não criar, completar ou rotular casos de piloto/benchmark; não executar ATTRACTOR em casos RGC nem produzir métricas RGC; não alterar Judge, Golden protegidos, manifestos, hashes congelados, fontes capturadas, fixtures congeladas, tags ou releases; não reescrever histórico; não chamar revisão própria ou da conta mantenedora de independente; não afirmar validação institucional, certificação ou prontidão de produção.
- **Ratificação retroativa:** Anderson declara que as PRs #266 (reorganização do README) e #267 (PDF v1.1) foram realizadas sob sua ordem verbal e ratifica expressamente essas alterações nesta data. A DEC-015 cobria apenas o manual técnico; esta ratificação não altera esse escopo histórico e não representa revisão independente das PRs #266 ou #267.
- **Revisão e auditoria:** toda revisão automatizada deve ser descrita como “revisão automatizada (não independente)”. O achado F-01 permanece aberto até que exista revisão humana independente documentada.
- **Regra de merge:** usar squash com mensagem `<título> (#n)`, seguida de 1–2 linhas e terminando exatamente com: “Mesclada sob a autorização DEC-016 do mantenedor; revisão automatizada, não independente (F-01 permanece aberto).”
- **Data de registro:** 2026-10-21. A presente decisão autoriza o processo de trabalho; cada decisão científica permanece sujeita a seu próprio registro e aprovação explícita.


## DEC-017: Registro ausente versus INVALID_PREDICTION

- **Data:** 2026-10-21
- **Estado:** PENDENTE — esta entrada é uma proposta para decisão explícita do mantenedor, não uma aprovação nem autorização de execução.
- **Pergunta:** no contrato de avaliação RGC, como distinguir um registro de predição ausente de uma predição presente cujo valor é inválido?
- **Estado atual do executor:** um registro ausente, duplicado ou inconsistente é falha de integridade e interrompe a execução; uma predição presente mas inválida é mantida no denominador e contabilizada como erro. A nota de consistência em `docs/eval/STATISTICS.md` e a proposta [AMENDMENT-PROPOSAL-2026-10-20-INVALID-PREDICTION.md](eval/AMENDMENT-PROPOSAL-2026-10-20-INVALID-PREDICTION.md) registram que a redação atual do pré-registro pode ser interpretada de modo diferente.
- **Opção A — recomendada, pendente de aprovação:** ausência/duplicidade/inconsistência interrompe por integridade; valor presente porém inválido conta como predição incorreta. **Prós:** separa falha de pipeline de erro do sistema, preserva denominador interpretável e corresponde ao comportamento atual do executor. **Contras:** exige redação normativa precisa e uma emenda datada ao pré-registro antes da avaliação confirmatória.
- **Opção B — interromper também em qualquer valor inválido:** **Prós:** contrato de entrada estrito e simples. **Contras:** não contabiliza como erro do sistema um valor inválido já produzido e exigiria mudar o executor/estatística; pode ocultar a taxa de saída inválida.
- **Opção C — contar ausência como erro, assim como valor inválido:** **Prós:** denominador fixo e análise mais simples. **Contras:** mistura ausência de registro (falha de integridade) com erro de predição e pode mascarar falhas de transporte/serialização.
- **Recomendação:** manter a Opção A, mas não a aplicar como decisão normativa até aprovação explícita. Se aprovada, registrar emenda datada no pré-registro e alinhar protocolo, executor e relatório antes de qualquer avaliação confirmatória.
- **Limites:** nenhum caso de piloto ou benchmark foi criado, completado, rotulado ou executado para esta análise; não há resultados RGC PT-BR novos. Esta decisão não altera a fixture congelada nem autoriza avaliação.

