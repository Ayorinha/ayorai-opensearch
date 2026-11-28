# Decisões aprovadas — AYORAI ATTRACTOR

Este arquivo registra decisões explícitas do mantenedor já aprovadas. Não substitui ADRs normativas; mantém a trilha de governança e autorização.

## Índice das aprovações registradas em DECISIONS-PENDING.md

Por razões históricas, várias decisões aprovadas têm o texto e o registro de aprovação em [DECISIONS-PENDING.md](DECISIONS-PENDING.md), e não neste arquivo. A tabela abaixo só as localiza; ela transcreve o estado e a data já registrados lá e não cria, amplia nem altera nenhuma aprovação. O texto de cada decisão continua sendo a fonte.

| ID | Assunto | Estado registrado |
|---|---|---|
| DEC-005 | r1-a: entrada inválida retorna 422 | Aprovada (2026-10-11) |
| DEC-007 (RGC) | Vocabulário de cinco vereditos do RGC | Aprovada (2026-10-15) |
| DEC-008 (RGC) | Autoria dos casos do RGC | Aprovada (2026-10-15) |
| DEC-009 | Abstenção avaliada como `UNVERIFIED` | Aprovada (2026-10-15) |
| DEC-010 | Afirmações compostas (opção A) | Aprovada (2026-10-16) |
| DEC-011 | Guia de anotação após o piloto 01 | Aprovada (2026-10-17) |
| DEC-013 | Autorização de execução e merge por agente naquele ciclo | Aprovada (2026-10-18); escopo limitado |
| DEC-014 | Baseline primário e descritivo do RGC | Aprovada (2026-10-18) |
| DEC-015 | Autorização da Etapa 2 (manual técnico) | Aprovada (2026-10-18) |
| DEC-016 | Trabalho autônomo e ratificação documental | Aprovada (2026-10-21) |
| DEC-017 | Registro ausente versus `INVALID_PREDICTION` | Aprovada (2026-10-21), opção A |
| DEC-018 | Escopo confirmatório de H1 | Aprovada (2026-10-21), opção A |
| DEC-019 | Bootstrap agrupado por artigo | Aprovada (2026-10-21), opção A |
| DEC-020 | Concordância entre anotadores | Aprovada (2026-10-21), opção A |
| DEC-021 | Teste confirmatório de H1 por componentes | Aprovada (2026-11-07), opção A |
| DEC-022 | IC95% de Cohen's kappa por componentes | Aprovada (2026-11-07), opção A |
| DEC-023 | Componentes conectados por artigos citados | Aprovada (2026-11-07), opção A |
| DEC-024 | Calibração e combinação de sinais no LLM-AggreFact | Aprovada (2026-11-08), opção B |
| DEC-027 | Reconciliação estatística do RGC | Aprovada (2026-11-14) |

As quatro que restavam pendentes nesse registro (DEC-001, DEC-003, DEC-004 e DEC-006) foram decididas em 2026-11-21; ver a seção abaixo.

## Decisões de 2026-11-21

- **Data da decisão:** 2026-11-21
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Forma:** resposta explícita do mantenedor às quatro perguntas, cada uma com a opção recomendada escolhida.

### DEC-001 — Lockfile e digests de imagem: encerrada como atendida

- A reprodutibilidade fica com o que já está implementado: `docker/Dockerfile` usa `python:3.12-slim` fixada por digest, e as dependências vêm de `docker/requirements.lock` com hashes (`pip install --require-hashes --only-binary=:all:`).
- `uv.lock` não é adotado. Mudar a ferramenta de lock exige nova decisão.

### DEC-003 — ADR-001: aceito

- O ADR-001 passa a `Accepted` em 2026-11-21. A conferência feita na aceitação está na nota datada do próprio ADR.

### DEC-004 — Nome do repositório e documentação comercial

- O repositório continua `ayorai-opensearch`; links, DOI e badges não mudam.
- Material comercial só descreve o que testes e avaliações demonstram, conforme a política de alegações do `CONTRIBUTING.md`.

### DEC-006 — Prioridade do motor de stance em português: opção A

- O motor de stance em português (ADR-008) é a próxima prioridade técnica.
- Condições:
  - medição estratificada com tamanho amostral e IC95%;
  - nada é ajustado ao Golden;
  - o benchmark RGC e seu protocolo não mudam;
  - o Judge não passa a fazer interpretação jurídica.
- Esta decisão define prioridade; não aprova implementação, modelo ou dependência, que seguem em PRs próprias.

## DEC-012 — Registro de auditoria verificável: decisões 1–4 da ADR-010

- **Data da decisão:** 2026-10-17
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** ACEITO, seguindo a recomendação técnica em todas as quatro perguntas.
  1. **Compromissos com sal** em vez de hashes diretos: a folha do log guarda `SHA-256(domain_label || salt || canonical_record)`; sal e registro ficam num armazenamento apagável, com controle de acesso, e no recibo do cliente.
  2. **Veredito só dentro do compromisso**, nunca em claro na folha.
  3. **Falha de gravação bloqueia:** no modo "registro obrigatório", sem evento gravado não há veredito; a API devolve erro.
  4. **Emenda à ADR-009 §15 aprovada** (registrada como §15.1): `audit_status`, `audit_receipt` e `Idempotency-Key`, campos aditivos fora de `result`, só com o registro ligado.
- **Continua em aberto:** escritor em Python ou Tessera (decidir por prova de conceito), testemunhas independentes e carimbo do tempo ICP-Brasil.
- **Execução:** em fases, uma PR por fase (ADR-010, "Implementation phasing"). A fase 1 é uma biblioteca isolada (árvore de Merkle RFC 6962 e compromissos), sem mudar API, banco, dependências ou o Judge.
- **Condições permanentes:** CI verde, revisão do SHA exato, nenhuma alteração de Golden, regras, hashes ou manifestos congelados.
- **Limite de maturidade:** até a fase 3 estar mesclada e implantada, nenhuma instalação pode ser descrita como tendo log de auditoria verificável.

## DEC-007 — Publicar a release v0.4.0?

- **Data da decisão:** 2026-10-11
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão de governança:** ACEITO COM RESSALVAS
- **Opção sobre a release:** OPÇÃO A — PUBLICAR
- **Decisão:** Aceitar o encerramento técnico da Onda 1 (PRs #147, #148 e #149) e da Fase 1 e autorizar a continuidade da Onda 2.
- **Autorização documental:** abrir e mesclar uma PR documental `docs: finalize v0.4.0 release metadata`, atualizando `docs/release/v0.4.0.md` para status `Released`, data `2026-10-11` e tag declarada `v0.4.0`; atualizar `CHANGELOG.md` para `[0.4.0] — 2026-10-11`; registrar `date-released: 2026-10-11` em `CITATION.cff`; e mover esta decisão da fila pendente para este registro aprovado.
- **Tag e publicação GitHub:** não criar automaticamente. Anderson criará manualmente a tag e a GitHub Release depois do merge da PR documental.
- **Correção obrigatória dos resultados:** nunca apresentar Path B 66,67% contra baseline 43,33% sem o contexto de ambas as versões. Golden v0: Path B = 43,33%, igual à classe majoritária. Golden v0.1: Path B = 66,67%, mas v0.1 foi reescrito após a observação dos resultados e não é evidência confirmatória independente. Relatar Golden v0 e v0.1 lado a lado em todos os relatórios e documentos relevantes.
- **Condições permanentes:** revisão independente do SHA exato de cada PR, CI verde, merge por SQUASH e artefatos congelados intocados. Nenhuma alteração de Golden, threshold ou manifesto congelado é autorizada por esta decisão.
- **Limite de maturidade:** a publicação v0.4.0 não afirma que o Judge 2.0.0 esteja totalmente implementado, que os Goldens de desenvolvimento demonstrem generalização em produção ou que haja certificação regulatória ou conformidade jurídica automática.

## Decisões de 2026-11-21 — ADR-010, decisões 5 a 7 (DEC-028 a DEC-030)

- **Data da decisão:** 2026-11-21
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Forma:** resposta explícita do mantenedor a três perguntas, cada uma com a opção recomendada escolhida. Também autorizou registrar as decisões nos arquivos protegidos e mesclar a PR com o CI verde.
- **Base:** análises em [adr/ADR-010-IMPLEMENTATION-PROPOSAL-2026-11-21.md](adr/ADR-010-IMPLEMENTATION-PROPOSAL-2026-11-21.md); POC isolada na PR #618; implementação e evidências na PR #623.

### DEC-028 — ADR-010, decisão 5: escritor Python

- **Decisão:** a rota (a) da ADR-010, um escritor em Python dentro do serviço, implementa as fases 2 e 3.
- **Base:** a POC isolada da PR #618 exercitou as duas rotas.
  - O escritor Python grava a chave de idempotência, o sal, o registro, a folha e o checkpoint numa só transação SQLite.
  - O Tessera exige um segundo armazenamento e um mecanismo de reconciliação ainda não implementado.
- **Consequências:**
  - o log grava num único host (SQLite, um escritor por vez) e não publica tlog-tiles;
  - o Tessera será reavaliado se houver gravação em mais de um host, se o p95 de gravação passar de 50 ms no hardware de produção ou se as testemunhas exigirem tlog-tiles.
- **Evidência:** PR #618 e PR #623 (testes, verificação cruzada com Go e medições).

### DEC-029 — ADR-010, decisão 6: testemunhas em duas etapas

- **Decisão:**
  1. Até haver testemunhas independentes, o operador guarda fora do servidor, pelo menos uma vez por dia, o checkpoint mais recente e o confere contra o log. Isso não é apresentado como testemunha independente.
  2. A fase 4 implementará o protocolo C2SP tlog-witness e buscará pelo menos duas testemunhas sem vínculo de controle com o operador, com preferência por instituições brasileiras tecnicamente adequadas.
- **Consequências:**
  - nenhuma afirmação de resistência ao operador antes de duas cossignaturas independentes ativas;
  - checkpoints incompatíveis são tratados como incidente: gravação congelada no modo `required`, os dois checkpoints preservados e o fato publicado.
- **Em aberto:** quem serão as testemunhas. Nenhuma foi contatada, e não há parceria.

### DEC-030 — ADR-010, decisão 7: carimbo do tempo ICP-Brasil adiado

- **Decisão:** adiar a contratação. Quando um uso exigir hora oponível a terceiros:
  - carimbar periodicamente o hash do checkpoint (nunca cada evento) numa ACT credenciada pela ICP-Brasil;
  - guardar e publicar o token RFC 3161 junto do checkpoint;
  - documentar a verificação com OpenSSL e a cadeia do ITI.
- **Pré-condições para contratar:**
  - lista vigente de ACTs e preços levantados;
  - parecer jurídico sobre o efeito probatório;
  - autorização expressa do mantenedor para o gasto.
- **Consequências:** até lá, `received_at` e os checkpoints têm hora declarada pelo operador, e não se afirma hora certificada.

## DEC-034 — Identidades repetidas no DEV fixado da Phase 1b (P3/A1)

- **Data da decisão:** 2026-11-28
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Forma:** escolha escrita do mantenedor ("eu escolho a opção A"), entre as opções A a D apresentadas depois da execução protegida minimal `46151543376`.
- **Contexto:** a primeira execução protegida sobre o DEV fixado do LLM-AggreFact (revisão `981dfd0b…`) parou, por desenho, na trava de identidades repetidas. A mensagem informou só contagens: 46 identidades (documento, afirmação e coorte) repetidas, 50 linhas extras, 5 identidades com rótulos divergentes entre as cópias. Nenhum conteúdo foi exposto e nenhum artefato foi gerado.
- **Decisão (opção A):**
  1. Cópias de uma identidade com o mesmo rótulo contam uma vez: fica uma cópia.
  2. Identidades cujas cópias têm rótulos divergentes são excluídas por inteiro. O pipeline nunca escolhe um rótulo gold.
  3. O manifesto registra as contagens da resolução (`identity_resolution`), sem conteúdo.
- **Opções não escolhidas:** B (excluir todas as 46 identidades repetidas), C (escolher um rótulo para os conflitos) e D (manter as cópias com identificador por linha).
- **Implementação:** `resolve_dev_identities` em `scripts/benchmarks/phase1b/common.py`, usada pelo construtor do manifesto, pela preparação dos artefatos e pelo mapa de documentos. Manifesto `phase1b-dev-manifest-v3`.
- **Limites:** vale só para o DEV da Phase 1b. Não altera Judge, Golden, RGC, thresholds, o pino do dataset nem os dados de origem. Não autoriza execução DEV completa nem TEST.

## DEC-033 — Retenção dos caches cifrados da Phase 1b DEV (P3/A1)

- **Data da decisão:** 2026-11-28
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Forma:** ordem de execução escrita do mantenedor, aprovando a opção A da proposta registrada em [DECISIONS-PENDING.md](DECISIONS-PENDING.md#dec-033--retenção-dos-caches-cifrados-da-phase-1b-dev-p3a1).
- **Decisão (opção A):**
  1. Caches cifrados gold e score: 30 dias, contados da execução DEV de origem.
  2. A re-agregação não renova o prazo: os caches reenviados herdam o que resta dos 30 dias, e uma origem vencida é recusada.
  3. Manifesto cifrado, entrada de inferência cifrada e shards: 7 dias.
  4. Relatórios agregados, sem dados por instância: 30 dias.
- **Implementação:** PR #644 (`phase1b-dev-full.yml`, `phase1b-dev-full-reaggregate.yml` e testes de contrato).
- **Limites:** não altera Judge, Golden, RGC, thresholds nem dados científicos. Não autoriza dispatch de workflows DEV ou TEST.

## DEC-032 — Tenant distinto de principal (ADR-013)

- **Data da decisão:** 2026-11-22
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Forma:** resposta explícita do mantenedor a quatro perguntas, com as opções recomendadas.
- **Decisão:**
  1. O tenant é um campo do arquivo de chaves, resolvido na leitura. O esquema da trilha não muda.
  2. Lê um rastro qualquer chave do mesmo tenant com `audit:read`. Entre tenants, 404.
  3. O log de verificação continua único, com o tenant no registro salgado (`ayorai.verify-record.v2`).
- **Autorização:** abrir as PRs da ADR-013 e da implementação e mesclar cada uma com CI verde, inclusive o CodeQL.
- **Registro normativo:** [adr/ADR-013-tenant.md](adr/ADR-013-tenant.md).

## DEC-031 — Chaves de API: escopos, expiração e revogação sem reinício (ADR-012)

- **Data da decisão:** 2026-11-21
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Forma:** resposta explícita do mantenedor a quatro perguntas, com as opções recomendadas.
- **Decisão:**
  1. Registro de chaves num arquivo JSON (`ATTRACTOR_API_KEYS_FILE`), relido sem reinício. A variável atual continua válida como modo legado.
  2. Arquivo inválido depois da subida: o serviço mantém o último válido, registra o erro e alerta. Na subida, não inicia.
  3. Quatro escopos: `verify`, `audit:write`, `audit:read` e `metrics`. Sem o escopo, 403.
  4. Tenant distinto de principal fica para uma ADR própria.
- **Autorização:** abrir as PRs da ADR-012 e da implementação e mesclar cada uma com CI verde e o diff revisado.
- **Registro normativo:** [adr/ADR-012-api-key-scopes-expiry-revocation.md](adr/ADR-012-api-key-scopes-expiry-revocation.md).

## DEC-008 — Publicar a release v0.5.0?

- **Data da decisão:** 2026-10-13
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão de governança:** ACEITO COM RESSALVAS
- **Opção sobre a release:** OPÇÃO A — PUBLICAR
- **Decisão:** autorizar a preparação da release v0.5.0 com os itens 2.1–2.7 do Judge 2.0, condicionada à revisão independente do SHA exato da PR e à aprovação dos seis checks obrigatórios.
- **Autorização documental:** abrir a PR `release: prepare v0.5.0 (Phase 2 — Judge 2.0)`, atualizar metadados de versão, changelog, guia, matriz de rastreabilidade e notas de release, preservando os artefatos congelados.
- **Compatibilidade:** adiar para v0.6.0 a remoção de `ResponseStatus`, dos campos `verification` e `confidence` e do caminho `r1-a` com regras 1.x. Nada é removido na v0.5.0.
- **Tag e publicação GitHub:** não criar automaticamente. Anderson criará manualmente a tag `v0.5.0` e a GitHub Release após o merge da PR.
- **Condições permanentes:** revisão independente do SHA exato, seis checks CI verdes e artefatos congelados intocados. Nenhuma alteração de Golden, thresholds, manifestos congelados ou `rules/judge-2.0.0.json` é autorizada.
- **Limite de maturidade:** não se afirma certificação regulatória, conformidade jurídica automática nem generalização em produção a partir dos Goldens de desenvolvimento. Hashes identificam conteúdo, mas não demonstram a verdade factual; a limitação documentada de forja em processo permanece.

## DEC-002 — Política de licença e proveniência das fontes

- **Data da decisão:** 2026-10-13
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** OPÇÕES 1 e 3 combinadas, conforme detalhado abaixo. A opção 2 (exceções caso a caso) não foi adotada.
- **Atos oficiais:** textos de leis, decretos, regulamentos, resoluções e demais atos oficiais podem ser usados no corpus e em fixtures, com base na Lei nº 9.610/1998, art. 8º, IV (fonte primária: https://www.planalto.gov.br/ccivil_03/leis/l9610.htm). Para cada documento é obrigatório registrar em `docs/annotation/SOURCES.md`: URL oficial, órgão emissor, data de publicação, data e hora de coleta, método de captura e SHA-256 dos bytes capturados.
- **Demais fontes:** comentários doutrinários, livros, notícias, páginas comerciais, bases privadas e qualquer material de terceiros só entram com licença ou permissão explícita registrada. Sem esse registro, ficam excluídos.
- **Separação pública e privada:** fixtures públicos e o conjunto de avaliação oculto têm controles e manifestos distintos; os casos ocultos nunca entram no repositório público (`docs/eval/PROTOCOL-GOLDEN-V1.md`).
- **Efeito sobre o benchmark RGC:** a Resolução Anatel nº 765/2023 é ato oficial e fica autorizada como fonte, **condicionada** à captura e ao registro de proveniência acima. A coleta pode começar somente depois desse registro, seguindo `docs/eval/PREREGISTRATION-RGC-v1.md`.
- **Limite:** esta decisão não afirma parceria, apoio ou validação da Anatel e não constitui parecer jurídico; antes de contrato com instituição, recomenda-se confirmação por assessoria jurídica.

