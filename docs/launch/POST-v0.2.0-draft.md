# Launch post draft — v0.2.0

> **Aviso histórico — 2026-10-23:** este documento registra uma versão, auditoria, avaliação ou rascunho anterior; preserve-o como evidência histórica e não o trate como estado atual nem como resultado de benchmark vigente. Consulte docs/STATUS.md and the approved notes for the target release.

> **Historical draft — not approved for publication.** Refresh all statements against the target release commit and verified Actions artifacts before use. The v0.2.0 figures below are historical baseline context, not current release metrics.

## Português

**De baseline honesto a um motor de verificação mensurável.**

Na Fase 0, o AYORAI ATTRACTOR congelou um golden set de 34 casos e 52 documentos sintéticos, com SHA-256 e baseline reproduzível pelo GitHub Actions.

O sistema atual atingiu **43,3333%**, exatamente a linha de base da classe majoritária PARTIALLY_SUPPORTED. Isso foi importante: o resultado mostrou que a fundação estava funcionando, mas que o motor de verificação ainda não fazia as distinções que o ADR-002 exige.

Antes do R1:
- acurácia: 43,3333%
- classe majoritária: PARTIALLY_SUPPORTED
- acima da classe majoritária: 0,00 pp

Depois do R1:
- acurácia: **[PREENCHER COM RESULTADO REAL DO ACTIONS]**
- acima da classe majoritária: **[PREENCHER] pp**
- holdout h0: **[PREENCHER COM RESULTADO REAL]**
- matriz de confusão: **[LINK PARA ARTIFACT/RELATÓRIO]**

A regra permanece a mesma: números só entram aqui depois de medidos pelo GitHub Actions. Consulte também [F1.2 Results](../eval/F1.2-RESULTS.md) e o [pré-registro do Golden v0.1](../eval/PREREGISTRATION-GOLDEN-v0.1.md); não misture resultados de versões diferentes nem apresente os conjuntos sintéticos como validação de produção.

## English

**From an honest baseline to a measurable verification engine.**

In Phase 0, AYORAI ATTRACTOR froze a golden set of 34 cases and 52 synthetic documents, with SHA-256 integrity and a reproducible GitHub Actions baseline.

The current system achieved **43.3333%**, exactly matching the majority-class baseline of PARTIALLY_SUPPORTED. That result mattered: it showed the foundation was measurable, while the verification engine still lacked the distinctions required by ADR-002.

Before R1:
- accuracy: 43.3333%
- majority class: PARTIALLY_SUPPORTED
- above-majority accuracy: 0.00 pp

After R1:
- accuracy: **[FILL ONLY FROM VERIFIED ACTIONS RESULT]**
- above-majority accuracy: **[FILL] pp**
- holdout h0: **[FILL ONLY FROM VERIFIED RESULT]**
- confusion matrix: **[ARTIFACT/REPORT LINK]**

The rule remains simple: no number is published here until GitHub Actions measures it. See [F1.2 Results](../eval/F1.2-RESULTS.md) and the [Golden v0.1 pre-registration](../eval/PREREGISTRATION-GOLDEN-v0.1.md); do not mix results from different versions or present synthetic sets as production validation.
