# Architecture Decision Records (ADRs)

Índice de decisões de arquitetura e avaliação do AYORAI ATTRACTOR. Os status e as datas abaixo são transcritos dos próprios arquivos; este índice não altera nem substitui os registros originais.

| Número | Título | Status declarado no arquivo | Data | Caminho |
|---|---|---|---|---|
| ADR-001 | Isolated Python Namespace | Proposed in A1 PR | 2026-09-30 | [`docs/adr/ADR-001-namespace.md`](ADR-001-namespace.md) |
| ADR-002 | Judge Rules and Evidence Verification | Accepted — 2026-09-30, approved by the maintainer together with Golden v0 (PR #12, merge b7df480) | 2026-09-30 | [`docs/adr/ADR-002-judge-rules.md`](ADR-002-judge-rules.md) |
| ADR-003 | Three-state stance semantics | Accepted | 2026-10-03 | [`docs/adr/ADR-003-three-state-stance.md`](ADR-003-three-state-stance.md) |
| ADR-004 | Claim as Verification Input | Accepted | 2026-10-03 | [`docs/adr/ADR-004-claim-as-input.md`](ADR-004-claim-as-input.md) |
| ADR-005 | Hybrid Multilingual Stance Detection | Accepted for F1 | 2026-10-03 | [`docs/adr/ADR-005-hybrid-multilingual-stance.md`](ADR-005-hybrid-multilingual-stance.md) |
| ADR-006 | Deterministic Metadata, Independence and Numeric Semantics | Accepted for F1.1 | 2026-10-03 | [`docs/adr/ADR-006-metadata-judge-rules.md`](ADR-006-metadata-judge-rules.md) |
| ADR-007 | AYORAI-PT-span: detector de trechos não sustentados em português | Proposed | 2026-10-03 | [`docs/eval/ADR-007.md`](../eval/ADR-007.md) |
| ADR-008 | AYORAI-PT-NLI: NLI comercial para português | Proposed | 2026-10-04 | [`docs/eval/ADR-008.md`](../eval/ADR-008.md) |
| ADR-009 | Deterministic adjudication contract and claim coverage | Proposed / Draft — awaiting maintainer approval | 2026-10-10 | [`docs/adr/ADR-009-deterministic-adjudication-contract.md`](ADR-009-deterministic-adjudication-contract.md) |

## Regras de manutenção

- Os arquivos ADR são a fonte de verdade para título, status, data e conteúdo.
- Ao alterar um ADR, atualize este índice na mesma pull request quando necessário.
- Não inferir aprovação, implementação, treinamento ou promoção a partir da presença de um ADR no índice.
- ADR-009 é um rascunho não normativo; ADR-002 continua vigente até aprovação explícita do mantenedor.
