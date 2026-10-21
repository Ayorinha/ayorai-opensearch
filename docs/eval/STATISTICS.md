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

**Nota de resolução (2026-10-21) — DEC-017, opção A aprovada:** a discrepância documental foi resolvida pela Emenda 7 de `PREREGISTRATION-RGC-v1.md` e de `PROTOCOL-GOLDEN-V1.md`. Registro ausente/duplicado, ID desconhecido ou rótulo humano ausente interrompe a execução; predição presente não mapeável para `judge2` vira `INVALID_PREDICTION`, permanece no denominador e conta como erro. Esta decisão não congela o protocolo nem autoriza avaliação confirmatória. Consulte [DEC-017 — Registro ausente versus INVALID_PREDICTION](../DECISIONS-PENDING.md#dec-017--registro-ausente-versus-invalidprediction).

A benchmark report should publish the dataset/suite version, case count, system commit, point accuracy, bootstrap interval, confusion matrix, and—when comparing two systems on identical cases—the paired McNemar result. The report should preserve system identifiers and raw metrics so downstream readers can make their own assessment.

For reproducibility, both systems in a paired comparison must use the same ordered gold-case sequence. Do not silently treat missing prediction records as ordinary model errors.


## Escopo confirmatório de H1 — DEC-018 (aprovada em 2026-10-21)

A hipótese H1 é testada somente sobre a partição oculta (~90 casos). Os casos públicos (~210) são usados para desenvolvimento e descrição, nunca para o teste confirmatório. O executor exige `--partition hidden|development`, registra o valor no relatório e não relata H1 como testada quando `development` é declarado. A declaração é um controle explícito de execução, não prova de que o arquivo realmente contém a partição correta; proveniência e isolamento continuam sendo gates humanos. Esta regra não congela o protocolo nem autoriza uma execução RGC.
