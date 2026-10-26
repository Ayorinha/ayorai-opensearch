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

**Nota vigente (2026-10-21) — DEC-017 Opção A aprovada:** registro ausente/duplicado, ID desconhecido, rótulo humano ausente ou arquivo inconsistente interrompe a execução; predição presente não mapeável para `judge2` recebe `INVALID_PREDICTION`, permanece no denominador e conta como erro. A decisão não congela o protocolo nem autoriza execução confirmatória. Consulte [DEC-017 — Registro ausente versus INVALID_PREDICTION](../DECISIONS-PENDING.md#dec-017--registro-ausente-versus-invalidprediction).

A benchmark report should publish the dataset/suite version, case count, system commit, point accuracy, bootstrap interval, confusion matrix, and—when comparing two systems on identical cases—the paired McNemar result. The report should preserve system identifiers and raw metrics so downstream readers can make their own assessment.

For reproducibility, both systems in a paired comparison must use the same ordered gold-case sequence. Do not silently treat missing prediction records as ordinary model errors.


## Proposta de escopo confirmatório de H1 — DEC-018 (PENDENTE)

> **Aviso editorial (2026-10-25) — bloco histórico/superado:** o texto abaixo preserva a proposta anterior à aprovação de DEC-018. Qualquer frase que diga que DEC-018 “permanece pendente” não representa o estado vigente. A regra aprovada está na seção “Escopo confirmatório de H1 — DEC-018 (aprovada em 2026-10-21)”, abaixo. O protocolo continua **[PROPOSTO]**, não congelado; este aviso não autoriza execução.

**Nota (2026-10-21):** superada pela Emenda 8 aprovada (DEC-018); mantida apenas como histórico.

A Opção A recomenda testar H1 somente sobre a partição oculta (~90 casos) e usar os casos públicos (~210) apenas para desenvolvimento e descrição. Esta é uma recomendação, não uma decisão aprovada; não altera o pré-registro nem autoriza execução. DEC-018 permanece pendente de decisão explícita do mantenedor. A declaração de partição e o isolamento real também exigem evidência humana e não devem ser tratados como resolvidos por documentação.

**Nota (2026-10-21):** superada pela Emenda 8 aprovada (DEC-018); mantida apenas como histórico.


## Escopo confirmatório de H1 — DEC-018 (aprovada em 2026-10-21)

A hipótese H1 é testada somente sobre a partição oculta (~90 casos). Os casos públicos (~210) são usados para desenvolvimento e descrição, nunca para o teste confirmatório. O executor exige `--partition hidden|development`, registra o valor no relatório e não relata H1 como testada quando `development` é declarado. A declaração é um controle explícito de execução, não prova de que o arquivo realmente contém a partição correta; proveniência e isolamento continuam sendo gates humanos. Esta regra não congela o protocolo nem autoriza uma execução RGC.


## Bootstrap por cluster de artigo — DEC-019 (aprovada em 2026-10-21)

O intervalo de confiança primário para H1 usa reamostragem de clusters de artigo; o bootstrap por caso é uma análise de sensibilidade. O campo `bootstrap_cluster_id` é obrigatório nos casos elegíveis da partição oculta. Caso com artigo principal usa seu identificador canônico; caso dependente de múltiplos artigos sem principal único usa `bundle:` com IDs canônicos únicos em ordem lexical, separados por `+`. `cited_article_ids` mantém a lista completa de referências. A amostragem sorteia com reposição tantos clusters quantos clusters únicos existem, inclui todos os casos do cluster sorteado e preserva multiplicidade de sorteios. Publicar método, seed, iterações, número de clusters e os dois intervalos. Esta decisão não congela o protocolo nem autoriza avaliação RGC.


## Concordância entre anotadores — DEC-020 (aprovada em 2026-10-21)

A ferramenta `evals/ptbr/rgc_agreement.py` calcula Cohen's kappa não ponderado para os cinco rótulos nominais definitivos, com gate pela estimativa pontual `κ ≥ 0,6`, IC95% percentil bootstrap por caso (10.000 reamostragens, seed `20261003`), concordância observada, matriz de confusão e marginais por classe. Exclui pares em que qualquer anotador usa `RULE_GAP` e reporta as exclusões separadamente. A ferramenta interrompe se os arquivos de anotação não tiverem IDs exatamente correspondentes ou contiverem duplicatas/rótulos inválidos. O esquema JSONL e os comandos estão no [guia de concordância entre anotadores](ANNOTATOR-AGREEMENT.md). Nenhum arquivo de anotação humana foi fornecido ou processado nesta execução.
