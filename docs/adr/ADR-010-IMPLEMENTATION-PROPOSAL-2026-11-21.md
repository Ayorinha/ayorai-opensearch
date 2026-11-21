# Proposta de registro — implementação das fases 2 e 3 da ADR-010

**Estado:** PROPOSTA, para o mantenedor inserir. Os arquivos de destino são protegidos (AGENTS.md §4): ADRs aceitas e decisões aprovadas. Por isso não foram editados por ferramenta automatizada. O código já está na PR que traz este arquivo.

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
- **Acceptance criteria still open:**
  - 1: key-custody threat model;
  - 4: cross-verification of inclusion and consistency proofs with an independent implementation;
  - 7: restore against an externally anchored checkpoint;
  - 8: latency and storage measured on deployment hardware.
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
