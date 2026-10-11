# Decisões aprovadas — AYORAI ATTRACTOR

Este arquivo registra decisões explícitas do mantenedor já aprovadas. Não substitui ADRs normativas; mantém a trilha de governança e autorização.

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

