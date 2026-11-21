# Architecture Decision Records (ADRs)

Índice de decisões de arquitetura e avaliação do AYORAI ATTRACTOR. Os status e as datas abaixo são transcritos dos próprios arquivos; este índice não altera nem substitui os registros originais.

| Número | Título | Status declarado no arquivo | Data | Caminho |
|---|---|---|---|---|
| ADR-001 | Isolated Python Namespace | Accepted — 2026-11-21, decisão do mantenedor (DEC-003) | 2026-09-30 | [`docs/adr/ADR-001-namespace.md`](ADR-001-namespace.md) |
| ADR-002 | Judge Rules and Evidence Verification | Accepted — 2026-09-30, approved by the maintainer together with Golden v0 (PR #12, merge b7df480) | 2026-09-30 | [`docs/adr/ADR-002-judge-rules.md`](ADR-002-judge-rules.md) |
| ADR-003 | Three-state stance semantics | Accepted | 2026-10-03 | [`docs/adr/ADR-003-three-state-stance.md`](ADR-003-three-state-stance.md) |
| ADR-004 | Claim as Verification Input | Accepted | 2026-10-03 | [`docs/adr/ADR-004-claim-as-input.md`](ADR-004-claim-as-input.md) |
| ADR-005 | Hybrid Multilingual Stance Detection | Accepted for F1 | 2026-10-03 | [`docs/adr/ADR-005-hybrid-multilingual-stance.md`](ADR-005-hybrid-multilingual-stance.md) |
| ADR-006 | Deterministic Metadata, Independence and Numeric Semantics | Accepted for F1.1 | 2026-10-03 | [`docs/adr/ADR-006-metadata-judge-rules.md`](ADR-006-metadata-judge-rules.md) |
| ADR-007 | AYORAI-PT-span: detector de trechos não sustentados em português | Proposed | 2026-10-03 | [`docs/eval/ADR-007.md`](../eval/ADR-007.md) |
| ADR-008 | AYORAI-PT-NLI: NLI comercial para português | Proposed | 2026-10-04 | [`docs/eval/ADR-008.md`](../eval/ADR-008.md) |
| ADR-009 | Deterministic adjudication contract and claim coverage | Accepted — 2026-10-10, maintainer decision; independent review and implementation pending | 2026-10-10 | [`docs/adr/ADR-009-deterministic-adjudication-contract.md`](ADR-009-deterministic-adjudication-contract.md) |
| ADR-010 | Verifiable audit log | Accepted in part — decisões 1–4 do mantenedor em 2026-10-17 (DEC-012); decisões 5–7 em aberto | 2026-10-17 | [`docs/adr/ADR-010-verifiable-audit-log.md`](ADR-010-verifiable-audit-log.md) |
| ADR-011 | Família de regras do Judge por rota (exceção ao prazo do ADR-009 §11) | Accepted — decisão do mantenedor em 2026-11-21 | 2026-11-21 | [`docs/adr/ADR-011-judge-family-per-route.md`](ADR-011-judge-family-per-route.md) |

## Regras de manutenção

- Os arquivos ADR são a fonte de verdade para título, status, data e conteúdo.
- Ao alterar um ADR, atualize este índice na mesma pull request quando necessário.
- Não inferir aprovação, implementação, treinamento ou promoção a partir da presença de um ADR no índice.
- ADR-009 foi aprovado pelo mantenedor em 2026-10-10 e substitui ADR-002 §§1 e 4; a revisão independente e a implementação permanecem pendentes.
- Desde 2026-11-21, a ADR-011 define a família de regras do Judge em cada rota e substitui, para `/v1/check`, `/v1/fields`, `/v2/audit` e `r1-a`, o prazo "até a v0.5.0" do ADR-009 §11. O texto do ADR-009 não foi alterado; leia os dois juntos.
- ADR-010: o que já existe e o que é futuro está em [ROADMAP.md](../ROADMAP.md), §1.
