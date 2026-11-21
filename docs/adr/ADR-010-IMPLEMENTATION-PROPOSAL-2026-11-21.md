# Proposta de registro — implementação das fases 2 e 3 da ADR-010

**Estado:** REGISTRADA em 2026-11-21. O mantenedor escolheu as opções recomendadas das decisões 5, 6 e 7 e autorizou o registro. Os textos abaixo foram inseridos na ADR-010 (seções de decisões e de status), no ADR-009 §15.1 e no `DECISIONS-APPROVED.md` (DEC-028 a DEC-030). Este arquivo fica como a análise que fundamenta essas decisões; a fonte normativa são os arquivos de destino.

## Texto proposto 1 — nova seção da `docs/adr/ADR-010-verifiable-audit-log.md`, antes de "Primary sources"

```markdown
## Implementation status (AAAA-MM-DD)

Recorded after implementation, without changing the decisions above.

| Phase | State | Where |
|---|---|---|
| 1. Core library | Done | `auditlog/merkle.py`, `auditlog/commitment.py` |
| 2. Checkpoints and storage | Done, with one deviation (below) | `auditlog/note.py`, `auditlog/store.py` |
| 3. Recording `/v1/verify` | Done | `api/verify_log.py`, `/v1/verify`, `GET /v1/verify/log` |
| 4. External state | Not started; decisions 6 and 7 open | — |

- **Decision 5 (writer route):** route (a), a Python writer (DEC-028). The isolated POC (PR #618) exercised both routes. Tessera stays the option if volume or witness integration requires it.
- **Phase 2.**
  - C2SP tlog-checkpoint and signed-note with Ed25519 (type 0x01). The signature over the public test vector of `golang.org/x/mod/sumdb/note` is byte-identical.
  - One writer at a time (`BEGIN IMMEDIATE`); several processes on one host may share the database.
  - Restart re-derives every leaf hash.
  - Mutation tests cover leaves, checkpoints, every receipt field, wrong keys, and databases reused with another origin or key.
- **Deviation:** leaves and checkpoints live in SQLite tables, not published as C2SP tlog-tiles. Tiles and an HTTP consistency endpoint are needed only when an external witness exists (phase 4).
- **Phase 3,** as in ADR-009 §15.1:
  - `ATTRACTOR_VERIFY_LOG_MODE` is `off`, `local` or `required`;
  - `audit_status` and `audit_receipt` stay outside `result`, and `output_sha256` is unchanged;
  - `Idempotency-Key`: same key and input return the same receipt; another input is a 409;
  - in `required` mode, a recording failure is a 503 with no verdict.

  The leaf carries only schema, `rules_sha256`, `software_id` and the salted commitment; the verdict exists only in the record.
- **Erasure, backup and recovery.**
  - `erase()` removes salt and record **and appends an erasure leaf** (`ayorai.verify-erasure.v1`, no personal data) under a new signed checkpoint. `verify_log()` flags any record erased or removed without its erasure leaf.
  - `backup()` makes a consistent copy.
  - `matches_checkpoint()` checks a checkpoint held outside the host against the log, exposing a restored older copy or rewritten history.
- **Acceptance criteria.**
  - 4 (independent cross-verification): done. Receipts, checkpoints and a consistency proof verified with `golang.org/x/mod/sumdb/note` and `transparency-dev/merkle` (`tests/auditlog/vectors/README.md`).
  - 8 (latency and storage): measured on the development container, not on deployment hardware. 50 000 events: about 1.2 ms per append (p95 1.7 ms), about 930 bytes per event, reopening in 0.15 s, full `verify_log()` in 7.7 s.
  - 1 (key custody): threat model written; HSM or KMS custody not implemented.
  - 7 (restore against an externally anchored checkpoint): `matches_checkpoint()` exists; external anchoring waits on decisions 6 and 7.
```

## Texto proposto 2 — fim do §15.1 da `docs/adr/ADR-009-deterministic-adjudication-contract.md`

```markdown
**Nota de implementação (AAAA-MM-DD).** A fase 3 da ADR-010 fixou:
- `audit_status` (`recorded` ou `not_recorded`) e `audit_receipt` (objeto `ayorai.verify-receipt.v1`), presentes só com `ATTRACTOR_VERIFY_LOG_MODE` diferente de `off`;
- cabeçalho `Idempotency-Key` com 1 a 128 caracteres visíveis; formato inválido devolve 422;
- conflito de chave: 409;
- falha de gravação no modo `required`: 503, sem veredito.

O `r1-a` não muda.
```

## Texto proposto 3 — `docs/DECISIONS-APPROVED.md` (e linha no índice de `DECISIONS-PENDING.md`)

```markdown
## DEC-028 — ADR-010, decisão 5: escritor Python

- **Data da decisão:** AAAA-MM-DD
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** a rota (a) da ADR-010, um escritor em Python dentro do serviço, implementa as fases 2 e 3.
- **Base:** a prova de conceito isolada da PR #618 exercitou as duas rotas. O escritor Python não exige um segundo serviço nem outra linguagem em produção. O Tessera continua sendo a opção se o volume ou as testemunhas exigirem.
- **Continuam em aberto:** testemunhas independentes e carimbo do tempo ICP-Brasil (decisões 6 e 7).
```


Até a inserção, a escolha do escritor está implementada, mas a decisão 5 continua formalmente em aberto no registro.

---

# Análises das decisões 5, 6 e 7 (2026-11-21)

Fato verificado: afirmação conferida no código, nos testes ou em fonte primária citada. Inferência: conclusão tirada desses fatos. Hipótese: algo que ainda precisa ser confirmado. Nenhuma das três decisões foi aprovada. Os textos abaixo esperam a decisão do mantenedor.

## Distinção de termos

| Mecanismo | O que prova | O que não prova | Estado no AYORAI |
|---|---|---|---|
| Assinatura digital (Ed25519) | que o portador da chave assinou aqueles bytes | quando assinou; que a chave não vazou; que o operador não assinou duas histórias | implementada (`auditlog/note.py`) |
| Checkpoint assinado (C2SP) | o log afirma: tamanho N, raiz R | que o operador mostra o mesmo checkpoint a todos; hora real | implementado; cada gravação gera um |
| Cosignatura de testemunha | uma parte independente viu o checkpoint e conferiu que ele estende o anterior | hora jurídica; correção do veredito | não implementada (decisão 6) |
| Carimbo do tempo ICP-Brasil (RFC 3161) | uma ACT credenciada atesta que aquele hash existia naquele instante, segundo sua política | correção do veredito; autoria; unicidade da história | não implementado (decisão 7) |

Inferência: a assinatura e o checkpoint protegem contra alteração por quem não tem a chave. Contra o próprio operador, só protegem recibos guardados pelo cliente, checkpoints guardados fora do servidor, testemunhas e carimbos do tempo.

## Modelo de confiança e custódia de chave (critério de aceite 1)

**Ativos:** a semente Ed25519 (`ATTRACTOR_VERIFY_LOG_KEY`), o banco SQLite (folhas, registros com veredito, sais, checkpoints) e os recibos com os clientes.

| Ameaça | Mitigação atual (fato verificado) | Resíduo |
|---|---|---|
| Alterar, apagar ou reordenar uma folha ou registro no banco | `verify_log()` recalcula cada hash e cada checkpoint; teste de adulteração | quem tem a chave pode reescrever tudo e reassinar |
| Apagar um registro sem deixar rastro | `verify_log()` exige a folha de apagamento | o mesmo |
| Voltar o banco para um backup antigo (rollback) | `matches_checkpoint()` contra um checkpoint guardado fora do host | sem checkpoint externo, nada detecta |
| Mostrar histórias diferentes a clientes diferentes (split view) | prova de consistência disponível (`consistency()`) | sem testemunha, o cliente isolado não percebe |
| Vazamento da semente | a semente vem do ambiente; nunca é gravada no banco (teste); o serviço não sobe sem ela nos modos `local` e `required` | quem tem a semente forja checkpoints; não há rotação nem revogação automáticas |
| Banco de outra origem ou chave | `_bind_origin` recusa abrir | — |
| Indisponibilidade da gravação | `required`: 503 sem veredito; `local`: `audit_status = "not_recorded"` | no `local`, um veredito pode existir sem registro, por escolha do operador |

**Requisitos de custódia propostos** (dependem do operador da implantação; não estão no código):
1. Gerar a semente fora do servidor de aplicação e guardá-la num gerenciador de segredos. Em produção, preferir HSM ou KMS que assine sem expor a semente. Isso exige trocar `NoteSigner` por um assinador remoto, o que é trabalho futuro.
2. Publicar a chave de verificação (`verifier_key`) num canal separado do serviço, com data de início.
3. Rotação: uma chave nova exige um log novo, com outra origem (`_bind_origin`). O último checkpoint da chave antiga deve ser registrado no log novo ou no canal público antes de descartar a chave.
4. Comprometimento: publicar o último checkpoint confiável e o tamanho até onde a história vale, abrir log novo e avisar os clientes que guardam recibos.
5. Guardar fora do host, pelo menos uma vez por dia, o checkpoint mais recente (`GET /v1/verify/log`). Isso resolve o rollback mesmo antes da decisão 6.

**Limite de confiança:** enquanto não houver testemunhas nem carimbo do tempo, o log é verificável contra adulteração por terceiros e por erro, mas não contra o operador que detém a chave.

## Decisão 5 — escritor Python × Tessera

| Critério | Escritor Python (implementado) | Tessera (POC da #618) |
|---|---|---|
| Segurança | sem novo serviço exposto; assinatura com `cryptography` | maduro e auditado pelo upstream; adiciona um processo Go e uma fronteira HTTP |
| Integridade | chave, sal, registro, folha e checkpoint numa única transação SQLite | idempotência fica fora do Tessera (antispam é best-effort, e o modo persistente é experimental); exige outbox |
| Persistência e recuperação | reinício reconstrói a árvore em 0,15 s com 50 mil folhas; backup consistente | durável no Tessera, mas dois armazenamentos |
| Reconciliação | não há: um só armazenamento | o scanner para a janela entre `Add` e o registro do índice não foi implementado |
| Desempenho (medido no contêiner de desenvolvimento) | cerca de 1,2 ms por gravação até 50 mil eventos | não medido em carga |
| Concorrência | um escritor por vez (`BEGIN IMMEDIATE`); vários processos num mesmo host | projetado para alto volume e vários nós |
| Complexidade | cerca de 500 linhas com testes; sem novo binário | binário Go, adaptador, outbox e scanner |
| Dependências | `cryptography` (já comum no ecossistema; hash no lock) | Go, Tessera e o driver de armazenamento |
| Manutenção e custo | uma linguagem; sem infraestrutura extra | duas linguagens e um serviço a operar |
| Compatibilidade arquitetural | casa com o serviço FastAPI e o SQLite já usados na auditoria | tiles C2SP nativos, que facilitam testemunhas |
| Lacuna | não publica tlog-tiles; um único host | — |

**Recomendação (inferência):** adotar o escritor Python agora. Ele resolve a idempotência sem a janela entre dois armazenamentos, que é o ponto fraco medido do Tessera. Reavaliar o Tessera se ocorrer um destes gatilhos: mais de um host gravando; volume que leve o p95 de gravação acima de 50 ms; ou testemunhas que exijam tlog-tiles e o custo de produzir tiles em Python ficar maior que integrar o Tessera.

**Texto definitivo proposto para a DEC-028:** o Texto proposto 3 acima, acrescido de:

```markdown
- **Consequências:** o log grava num único host (SQLite, um escritor por vez); não publica tlog-tiles; a idempotência e a gravação ficam na mesma transação. A troca para o Tessera será reavaliada se houver gravação em mais de um host, p95 de gravação acima de 50 ms no hardware de produção, ou exigência de tlog-tiles pelas testemunhas da decisão 6.
- **Evidência:** PR #618 (POC das duas rotas); PR #623 (implementação, testes, verificação cruzada com Go e medições).
```

## Decisão 6 — testemunhas independentes

**Ameaças mitigadas:** split view e reescrita da história pelo operador. A testemunha guarda o último checkpoint de cada log e só cossigna o novo depois de verificar a prova de consistência (C2SP tlog-witness). O cliente pode exigir um quórum de cossignaturas antes de confiar num recibo. Ela não mitiga: veredito errado, vazamento da chave do log antes da primeira cossignatura, nem a hora jurídica.

**Opções:**
1. Rede pública de testemunhas do ecossistema transparency-dev (OmniWitness/ArmoredWitness). Fato: implementam tlog-witness e monitoram logs públicos. Hipótese a confirmar: se aceitam um log novo, de terceiros, e com que critério. Custo direto zero; exige servir o checkpoint e as provas por HTTP no formato C2SP.
2. Testemunhas institucionais convidadas (por exemplo, universidades ou parceiros). Independência real depende de não terem vínculo de controle com o operador. Hipótese: ninguém foi contatado; não há parceria.
3. Testemunha operada pelo próprio mantenedor fora do servidor. É barato e detecta rollback, mas não é independente: não mitiga o operador.
4. Publicação periódica do hash do checkpoint em log público (Sigstore Rekor, entrada `hashedrekord`). Não é cossignatura; é âncora pública de existência.

**Publicação e divergência:** expor `GET /checkpoint` e a prova de consistência no formato tlog-witness, ou tiles. Ao receber duas cossignaturas de checkpoints incompatíveis do mesmo tamanho, tratar como incidente: congelar gravação no modo `required`, preservar ambos os checkpoints e publicar.

**Recuperação:** a testemunha guarda o último checkpoint aceito. Um log restaurado de backup antigo é recusado por ela, o que é desejável. O procedimento é publicar o incidente e abrir log novo (origem nova).

**Custos:** opção 3, horas de manutenção; opções 1 e 2, implementação do endpoint tlog-witness (estimativa, não medida: poucos dias) e acordo com terceiros; opção 4, sem custo direto, com dependência de serviço estrangeiro.

**Recomendação (inferência):** em duas etapas. Agora, a opção 3 com checkpoint diário guardado fora do host, sem afirmar independência. Depois, pelo menos duas testemunhas independentes (opções 1 ou 2), preferindo instituições brasileiras quando forem tecnicamente adequadas (AGENTS.md §6.1). A fase 4 só começa com essa aprovação.

**Texto proposto para registro (não aprovado):**

```markdown
## DEC-029 — ADR-010, decisão 6: testemunhas

- **Data da decisão:** AAAA-MM-DD
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** (1) até haver testemunhas independentes, o operador guarda fora do servidor, pelo menos diariamente, o checkpoint mais recente e o confere com `matches_checkpoint()`; isso não é apresentado como testemunha independente. (2) A fase 4 implementará o protocolo C2SP tlog-witness e buscará pelo menos duas testemunhas sem vínculo de controle com o operador, com preferência por instituições brasileiras tecnicamente adequadas.
- **Consequências:** nenhuma afirmação de resistência ao operador antes de duas cossignaturas independentes ativas; checkpoints incompatíveis são tratados como incidente.
- **Em aberto:** quem serão as testemunhas; nenhuma foi contatada.
```

## Decisão 7 — carimbo do tempo ICP-Brasil

**Necessidade.** O log já prova ordem e integridade. Não prova a hora: o campo `received_at` é declarado pelo próprio serviço. O carimbo do tempo de uma ACT credenciada é a forma de ter uma hora atestada por terceiro dentro da ICP-Brasil. Inferência: só é necessário se algum uso exigir prova de hora oponível a terceiros, como perícia, processo administrativo ou contrato. Para pesquisa e auditoria técnica, as testemunhas e os checkpoints datados pelo operador bastam.

**Base normativa (fato, fontes do ITI):**
- DOC-ICP-11 (visão geral do sistema de carimbo do tempo), baseado nas RFC 3161 e 3628 e no ETSI TS 101 861;
- DOC-ICP-12 (práticas das ACTs) e DOC-ICP-13 (requisitos mínimos das políticas);
- DOC-ICP-11.01 e 11.02 (rede de carimbo do tempo e sincronização);
- a versão vigente de cada um precisa ser confirmada no repositório do ITI antes da contratação.

**Autoridades aplicáveis.** Só ACTs credenciadas, listadas pelo ITI em "Entes da ICP-Brasil → Autoridades de Carimbo do Tempo". A lista atual e os preços não foram verificados nesta análise. Precisam ser levantados direto no ITI e com as ACTs.

**Alternativas de integração:**
1. Carimbar periodicamente (por exemplo, uma vez por dia) o hash SHA-256 do checkpoint mais recente, nunca cada evento. Isso evita custo por requisição e não vaza o ritmo de uso.
2. Usar uma ACT estrangeira ou gratuita (RFC 3161). É tecnicamente igual, mas sem o efeito da ICP-Brasil.
3. Não usar carimbo e manter só testemunhas.

**Verificação independente.** A resposta RFC 3161 (`TimeStampToken`, CMS) pode ser verificada com OpenSSL (`openssl ts -verify`) e a cadeia ICP-Brasil publicada pelo ITI, sem depender do AYORAI. O token seria guardado ao lado do checkpoint e publicado com ele.

**Dependências.** Contrato com a ACT, credencial de acesso, a cadeia de certificados do ITI e uma rotina agendada. A biblioteca `cryptography` não monta pedidos RFC 3161. A geração pode usar o OpenSSL (`openssl ts -query`) ou uma biblioteca a avaliar com os critérios do AGENTS.md §6.1.

**Evidências produzidas.** Um token por período, ligando o hash do checkpoint a uma hora atestada pela ACT.

**Limitações:**
- Técnicas: o carimbo atesta que o hash existia naquele instante. Não atesta o conteúdo do veredito, a correção do Judge, nem que não exista outra história. A granularidade é o período escolhido.
- Jurídicas (inferência, não parecer jurídico): a MP 2.200-2/2001 e a Lei 14.063/2020 tratam da presunção de veracidade de documentos assinados com certificado ICP-Brasil. O efeito probatório de um carimbo sobre um hash de checkpoint precisa de análise jurídica antes de qualquer afirmação pública.

**Custos.** Variáveis, por carimbo ou por pacote, definidos por cada ACT. Não levantados. Nada foi contratado.

**Recomendação (inferência):** não contratar agora. Registrar a decisão como "adiada até existir um uso que exija hora oponível a terceiros", com integração periódica sobre o checkpoint quando isso acontecer. Esse caminho mantém a soberania tecnológica como objetivo, porque usa a infraestrutura nacional, sem custo antes da necessidade.

**Texto proposto para registro (não aprovado):**

```markdown
## DEC-030 — ADR-010, decisão 7: carimbo do tempo ICP-Brasil

- **Data da decisão:** AAAA-MM-DD
- **Decisor e mantenedor:** Anderson Leon Ayora
- **Decisão:** adiar a contratação. Quando um uso exigir hora oponível a terceiros, carimbar periodicamente o hash do checkpoint (nunca cada evento) numa ACT credenciada pela ICP-Brasil, guardar e publicar o token RFC 3161 junto do checkpoint, e documentar a verificação com OpenSSL e a cadeia do ITI.
- **Pré-condições para contratar:** lista vigente de ACTs e preços levantados; parecer jurídico sobre o efeito probatório; autorização expressa do mantenedor para o gasto.
- **Consequências:** até lá, `received_at` e os checkpoints têm hora declarada pelo operador; nenhuma afirmação de hora certificada.
```

## Resumo dos bloqueios

| Item | Estado | Depende de |
|---|---|---|
| Fases 2 e 3 | implementadas e testadas (PR #623) | merge autorizado pelo mantenedor |
| Status na ADR-010 e nota no ADR-009 | textos 1 e 2 prontos | inserção pelo mantenedor (arquivos protegidos) |
| Decisão 5 (DEC-028) | recomendação e texto prontos | aprovação do mantenedor |
| Decisão 6 (DEC-029) | recomendação e texto prontos | aprovação; escolha e contato de testemunhas |
| Decisão 7 (DEC-030) | recomendação e texto prontos | aprovação; levantamento de ACTs e preços; parecer jurídico |
| Fase 4 | não iniciada | decisões 6 e 7 |
| Custódia em HSM ou KMS | requisitos escritos | infraestrutura da implantação |

Fontes: [DOC-ICP-11 v1.3](https://www.gov.br/iti/pt-br/assuntos/legislacao/documentos-principais/doc-icp-11_versao-1-3.pdf), [DOC-ICP-11 v2.0](https://www.gov.br/iti/pt-br/assuntos/legislacao/documentos-principais/doc-icp-11-v-2-0-anexo-resolucao-171.pdf), [DOC-ICP-12](https://www.gov.br/iti/pt-br/assuntos/legislacao/documentos-principais/doc-icp-12versao-1-3.pdf), [entes da ICP-Brasil](https://www.gov.br/iti/pt-br/assuntos/icp-brasil/entes-da-icp-brasil), [Lei 14.063/2020](https://planalto.gov.br/ccivil_03/_ato2019-2022/2020/Lei/L14063.htm), [C2SP tlog-cosignature](https://github.com/C2SP/C2SP/blob/main/tlog-cosignature.md), [transparency-dev witness](https://pkg.go.dev/github.com/transparency-dev/witness), [rede de testemunhas](https://blog.transparency.dev/can-i-get-a-witness-network).
