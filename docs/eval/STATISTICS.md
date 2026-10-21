# Evaluation Statistics

ATTRACTOR keeps decision logic separate from statistical reporting.

- **6×6 confusion matrix:** fixed to the six ADR-002 Judge verdict states. This is a legacy/statistical contract for that vocabulary, not a universal matrix for every evaluation.
- **RGC PT-BR vocabulary:** the RGC executor uses the five `judge2` states defined by Judge 2.0. Its confusion matrix follows that vocabulary and the documented treatment of `INVALID_PREDICTION`; the legacy ADR-002 6×6 matrix must not be interpreted as the RGC label space.
- **Bootstrap:** the RGC runner reports deterministic percentile 95% confidence intervals for accuracy, balanced accuracy, and macro-F1, using 10,000 resamples and seed `20261003`. One shared resample sequence is used for all three metrics. The runner sorts each metric's bootstrap values and selects the order statistics at indices `floor(0.025 × (B − 1))` and `floor(0.975 × (B − 1))`, where `B` is the number of resamples. The implementation does not interpolate between order statistics.
- **Balanced accuracy in bootstrap replicates:** each replicate averages recall over the reference labels present in that replicate. If a reference label is absent from a replicate, it does not contribute a recall term for that replicate. The full-sample report separately lists reference states absent from the evaluation set.
- **Macro-F1:** the RGC runner computes macro-F1 over the union of reference and predicted labels in each sample, including `INVALID_PREDICTION` when present; its F1 is zero because it never appears in the reference labels.
- **McNemar:** exact two-sided test for paired predictions from two systems on the same cases.
- **Arena:** compares multiple systems on the same cases and reports accuracy, confidence intervals, confusion matrices, and paired McNemar results without selecting or ranking a winner.

These functions consume only expected and predicted labels. They do not alter verdicts, call an LLM, or select a benchmark winner. These implementation details describe the current RGC runner; they do not freeze the proposed RGC protocol or authorize a confirmatory run.

## Missing records versus invalid predictions

A missing prediction record is an input-integrity problem: the prediction file does not contain exactly one prediction for every evaluable case. Reject the run rather than silently dropping the case or inventing a prediction.

For the RGC executor, a present prediction that cannot be mapped to the `judge2` vocabulary is represented as `INVALID_PREDICTION`. It remains in the evaluation denominator and counts as an incorrect prediction. This is distinct from a missing record, duplicate case, missing human label, or unknown case ID, which must stop the run. The report should retain the invalid-prediction count.

**Nota histórica (PR #323, 2026-10-21; não vigente):** uma atualização anterior marcou a Opção A como aprovada e descreveu a discrepância como resolvida. Esta linha é preservada como histórico da alteração.

**Nota vigente (2026-10-21) — DEC-017 PENDENTE:** o executor atual distingue falha de integridade de uma predição presente inválida, mas a interpretação normativa continua pendente de decisão explícita e emenda datada aprovada. Não considerar esta nota uma aprovação nem executar avaliação confirmatória. Consulte [DEC-017 — Registro ausente versus INVALID_PREDICTION](../DECISIONS-PENDING.md#dec-017--registro-ausente-versus-invalidprediction) e a [proposta de emenda pendente](AMENDMENT-PROPOSAL-2026-10-20-INVALID-PREDICTION.md).

A benchmark report should publish the dataset/suite version, case count, system commit, point accuracy, bootstrap interval, confusion matrix, and—when comparing two systems on identical cases—the paired McNemar result. The report should preserve system identifiers and raw metrics so downstream readers can make their own assessment.

For reproducibility, both systems in a paired comparison must use the same ordered gold-case sequence. Do not silently treat missing prediction records as ordinary model errors.


## Escopo confirmatório de H1 — DEC-018 aprovada (2026-10-21)

H1 só é testada na partição oculta (~90 casos). Os ~210 casos públicos são exclusivamente para desenvolvimento e métricas descritivas/exploratórias. O executor registra `partition` e em `development` não marca H1 como testada. O campo declarado não prova isolamento real; esse gate depende de evidência humana. O protocolo permanece [PROPOSTO] e nenhuma execução RGC é autorizada por esta documentação.
