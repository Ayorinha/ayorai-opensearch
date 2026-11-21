# ADR-011 — Família de regras do Judge por rota (exceção ao prazo do ADR-009 §11)

- **Status:** Accepted — decisão do mantenedor em 2026-11-21: registrar a exceção, sem mudar comportamento.
- **Data:** 2026-11-21
- **Decisor:** Anderson Leon Ayora
- **Relaciona-se com:** ADR-002 (regras 1.x), ADR-009 (contrato `r2-a`), auditoria técnica de 2026-11-20 (achado P1-3).
- **Não altera:** o texto do ADR-002 nem o do ADR-009, regras do Judge, Golden, manifestos ou hashes congelados.

## Contexto

O ADR-009 §11 diz que as regras 1.x "permanecem executáveis e historicamente preservadas até a v0.5.0". O projeto está na v0.8.0, e três rotas ainda usam o Judge do ADR-002 (`src/ayorai_attractor/verification/judge.py`, via `claim_pipeline.py` e `document_check.py`):

| Rota | Família de regras | Vocabulário |
|---|---|---|
| `POST /v1/check` | ADR-002 (1.x), por `document_check` | `verified`, `supported`, `partially_supported`, `unverified`, `refuted`, `conflicting` |
| `POST /v1/fields` | ADR-002 (1.x), por `document_check` | idem |
| `POST /v2/audit` | ADR-002 (1.x), por `document_check` | idem |
| `POST /v1/verify` com `schema_version = "r1-a"` | ADR-002 (1.x) | contrato de fio `r1-a` |
| `POST /v1/verify` com `schema_version = "r2-a"` | ADR-009 / Judge 2.0.0 (`rules/judge-2.0.0.json`) | `SUPPORTED`, `REFUTED`, `UNVERIFIED`, `PARTIALLY_SUPPORTED`, `CONFLICTING` |

A auditoria de 2026-11-20 registrou essa diferença como P1-3: havia dois contratos de Judge em uso, e o prazo do ADR-009 tinha passado sem decisão.

## Decisão

1. **Exceção registrada.** `/v1/check`, `/v1/fields` e `/v2/audit` continuam com as regras do ADR-002 como contrato normativo. O caminho `r1-a` do `/v1/verify` também. O prazo "até a v0.5.0" do ADR-009 §11 deixa de valer para essas rotas e passa a valer o que esta ADR define.
2. **Uma família por rota.** Cada rota usa uma única família de regras, a da tabela acima. Nenhuma rota mistura as duas famílias num mesmo veredito.
3. **O ADR-009 continua normativo onde se aplica:** `/v1/verify` com `r2-a` e o benchmark RGC (vocabulário `judge2`, Emenda 2 do protocolo).
4. **Migração só planejada.** Levar `/v1/check`, `/v1/fields` ou `/v2/audit` para o `r2-a` muda o vocabulário e os vereditos devolvidos. Isso só acontece numa versão maior, com:
   - ADR própria;
   - contrato novo publicado no OpenAPI e no `docs/api/CHANGELOG-API.md`;
   - período de coexistência;
   - medição nos Golden v0 e v0.1, relatada caso a caso.

   Nada disso é autorizado por esta ADR.
5. **Garantia em teste.** `tests/test_judge_family_per_route.py` falha se o pipeline do `/v1/check` deixar de usar o Judge do ADR-002 ou se `document_check` passar a importar o Judge 2.0 sem uma ADR de migração.

## Consequências

- O achado P1-3 fica resolvido como decisão registrada, não como migração.
- Quem consome a API sabe qual vocabulário cada rota devolve, e o comportamento atual não muda.
- O vocabulário `verified` continua existindo nas rotas 1.x. No RGC ele não é rótulo de referência (Emenda 2).
- A dívida continua visível: duas famílias de regras convivem, e a migração exige o plano do item 4.

## Verificação

- `tests/test_judge_family_per_route.py`.
- Testes existentes de contrato de fio `r1-a` e de contrato `r2-a` (ADR-009, "Implementação").
