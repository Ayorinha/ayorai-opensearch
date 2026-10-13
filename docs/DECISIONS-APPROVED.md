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

