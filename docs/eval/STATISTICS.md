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


## Registro histórico — proposta de escopo confirmatório de H1 — DEC-018 (estado anterior à aprovação)

> **Aviso editorial (2026-10-25) — bloco histórico/superado:** o texto abaixo preserva a proposta anterior à aprovação de DEC-018. Qualquer frase que diga que DEC-018 “permanece pendente” não representa o estado vigente. A regra aprovada está na seção “Escopo confirmatório de H1 — DEC-018 (aprovada em 2026-10-21)”, abaixo. O protocolo continua **[PROPOSTO]**, não congelado; este aviso não autoriza execução.

**Nota (2026-10-21):** superada pela Emenda 8 aprovada (DEC-018); mantida apenas como histórico.

**Texto histórico (estado anterior à aprovação de 2026-10-21):** a Opção A recomendava testar H1 somente sobre a partição oculta (~90 casos) e usar os casos públicos (~210) apenas para desenvolvimento e descrição. Naquele momento, a proposta ainda não havia sido aprovada. Esse trecho foi preservado para rastreabilidade e não representa o estado vigente. A declaração da partição e o isolamento real continuam exigindo evidência humana; documentação, por si só, não comprova esses controles.

**Nota (2026-10-21):** superada pela Emenda 8 aprovada (DEC-018); mantida apenas como histórico.


## Escopo confirmatório de H1 — DEC-018 (aprovada em 2026-10-21)

A hipótese H1 é testada somente sobre a partição oculta (~90 casos). Os casos públicos (~210) são usados para desenvolvimento e descrição, nunca para o teste confirmatório. O executor exige `--partition hidden|development`, registra o valor no relatório e não relata H1 como testada quando `development` é declarado. A declaração é um controle explícito de execução, não prova de que o arquivo realmente contém a partição correta; proveniência e isolamento continuam sendo gates humanos. Esta regra não congela o protocolo nem autoriza uma execução RGC.


## Bootstrap por cluster de artigo — DEC-019 (aprovada em 2026-10-21)

O intervalo de confiança primário para H1 usa reamostragem de clusters de artigo; o bootstrap por caso é uma análise de sensibilidade. O campo `bootstrap_cluster_id` é obrigatório nos casos elegíveis da partição oculta. Caso com artigo principal usa seu identificador canônico; caso dependente de múltiplos artigos sem principal único usa `bundle:` com IDs canônicos únicos em ordem lexical, separados por `+`. `cited_article_ids` mantém a lista completa de referências. A amostragem sorteia com reposição tantos clusters quantos clusters únicos existem, inclui todos os casos do cluster sorteado e preserva multiplicidade de sorteios. Publicar método, seed, iterações, número de clusters e os dois intervalos. Esta decisão não congela o protocolo nem autoriza avaliação RGC.


## Concordância entre anotadores — DEC-020 (aprovada em 2026-10-21)

A ferramenta `evals/ptbr/rgc_agreement.py` calcula Cohen's kappa não ponderado para os cinco rótulos nominais definitivos, com gate pela estimativa pontual `κ ≥ 0,6`, IC95% percentil bootstrap por caso (10.000 reamostragens, seed `20261003`), concordância observada, matriz de confusão e marginais por classe. Exclui pares em que qualquer anotador usa `RULE_GAP` e reporta as exclusões separadamente. A ferramenta interrompe se os arquivos de anotação não tiverem IDs exatamente correspondentes ou contiverem duplicatas/rótulos inválidos. O esquema JSONL e os comandos estão no [guia de concordância entre anotadores](ANNOTATOR-AGREEMENT.md). Nenhum arquivo de anotação humana foi fornecido ou processado nesta execução.

## RGC PT-BR — decisões estatísticas por componentes (DEC-021 a DEC-023; 2026-11-07)

**Estado:** DEC-021, DEC-022 e DEC-023 foram aprovadas pelo mantenedor em 2026-11-07. Esta seção registra a especificação estatística aprovada; não altera o pré-registro, o protocolo, o executor ou a autorização de execução. A implementação permanece pendente.

### Unidade final de reamostragem e permutação — DEC-023

A unidade estatística final é o componente conectado de casos, construído a partir de `cited_article_ids`:

1. Cada caso é um vértice.
2. Dois casos pertencem à mesma componente quando compartilham ao menos um ID de artigo citado. A relação é transitiva.
3. Para cada componente, reunir os IDs de artigos únicos, ordenar lexicalmente e formar `component:` + IDs unidos por `+`.
4. A componente é uma única unidade de reamostragem ou permutação; todos os casos que a integram permanecem juntos.
5. Reportar o número de valores distintos de `bootstrap_cluster_id` antes da união, o número de componentes depois da união, os casos por componente e o tamanho da maior componente.

O `bootstrap_cluster_id` de DEC-019 continua sendo metadado de entrada e permite informar as unidades anteriores à união. A lista completa `cited_article_ids`, e não apenas o artigo principal ou os membros de um `bundle:`, determina as conexões transitivas. Componentes grandes reduzem o número efetivo de unidades; a contagem de casos, isoladamente, não demonstra que há unidades independentes suficientes.

### Teste confirmatório de H1 por sign-flip — DEC-021

Para cada componente `k`:

- `a_k`: casos em que o sistema acerta e a Baseline B erra;
- `b_k`: casos em que a Baseline B acerta e o sistema erra;
- `d_k = a_k - b_k`.

A estatística observada é `T_obs = sum_k d_k`. A ponderação é pelo número de casos de cada componente; componentes com `d_k = 0` permanecem na análise.

- Se `K <= 20`, enumerar todas as `2^K` combinações de sinais. O p-valor bilateral é a fração de combinações com `|T*| >= |T_obs|`.
- Se `K > 20`, usar 10.000 sorteios com seed `20261003` e correção de Monte Carlo `p = (1 + E) / (1 + 10_000)`, em que `E` é o número de permutações extremas.
- Reportar `K`, o número de combinações consideradas e a resolução mínima teórica `2 / 2^K`.
- Se `K < 6`, registrar que a resolução não permite atingir `p < 0,05`. Não trocar o teste nem reduzir o nível de significância para contornar essa limitação.

A validade do sign-flip depende da permutabilidade dos resultados sistema/Baseline B dentro de cada componente sob H0. Essa é uma hipótese metodológica, não uma propriedade garantida pelo algoritmo nem pela construção do grafo. A interpretação do p-valor deve declarar essa condição e reconhecer que componentes por artigo não provam independência entre componentes.

**Sensibilidades, não testes primários:** McNemar exato por caso e o método de Obuchowski (1998) para proporções pareadas agrupadas. O artigo de Obuchowski estende a comparação de proporções correlacionadas a dados amostrados em clusters e alerta que o tamanho do teste de McNemar pode exceder o nível nominal na presença de correlação intraclasse. Referência: [Obuchowski, N. A. (1998), *On the comparison of correlated proportions for clustered data*, Statistics in Medicine, 17(13), 1495–1507](https://doi.org/10.1002/(SICI)1097-0258(19980715)17:13%3C1495::AID-SIM863%3E3.0.CO;2-I); [PubMed PMID 9695194](https://pubmed.ncbi.nlm.nih.gov/9695194/). Ambos os métodos são análises de sensibilidade descritivas segundo DEC-021, não substitutos do sign-flip confirmatório.

### IC95% de Cohen's kappa por componente — DEC-022

- Calcular o IC95% percentil de Cohen's kappa não ponderado por bootstrap de componente, com 10.000 reamostragens e seed `20261003`.
- Contabilizar as reamostras em que kappa é indefinido e excluí-las do cálculo do intervalo.
- Publicar a contagem e a proporção de reamostras indefinidas; se a proporção superar 5%, marcar o intervalo como **instável**. Se nenhuma reamostra produzir kappa definido, o intervalo deve ser reportado como indisponível, nunca inventado.
- O gate permanece na estimativa pontual `kappa >= 0,6`. O IC95% não altera esse gate.
- Permanecem obrigatórios a concordância observada, a matriz de confusão, as marginais por classe e a contagem de pares excluídos por `RULE_GAP`, conforme DEC-020.

Para reprodutibilidade da implementação, o procedimento de sorteio dos componentes, a preservação da multiplicidade de componentes selecionados e a convenção de quantis devem ser registrados explicitamente antes de gerar qualquer relatório humano. A DEC-022 fixa iterações, seed e tratamento de indefinição, mas não descreve esses detalhes operacionais.

### Estado de implementação — não confundir especificação com execução

No estado de código consultado em 2026-11-07:

- `evals/ptbr/rgc_eval.py` calcula o bootstrap por `bootstrap_cluster_id` de DEC-019 e valida `cited_article_ids`, mas não constrói componentes conectados nem implementa o sign-flip de DEC-021.
- `evals/ptbr/rgc_agreement.py` ainda reamostra casos individualmente e publica `ci95_case_bootstrap`; não implementa o bootstrap por componente de DEC-022.
- Os testes existentes cobrem as regras anteriores com dados sintéticos; não há testes para a união transitiva, o sign-flip ou o bootstrap de kappa por componente.

Essas diferenças são pendências de implementação, não resultados do benchmark. Não há casos RGC reais, anotação humana processada ou estatística observada nesta atualização. O PR que registrou DEC-021–DEC-023 alterou somente `docs/DECISIONS-PENDING.md`; não implementou os métodos.

### Alinhamento documental obrigatório antes de qualquer execução

As decisões aprovadas mais recentes ainda não estão reconciliadas com todos os documentos normativos anteriores:

- O §5 de `PREREGISTRATION-RGC-v1.md` ainda usa o p-valor do McNemar como condição de sucesso de H1, enquanto DEC-021 define o sign-flip por componente como teste confirmatório e relega McNemar à sensibilidade.
- A Emenda 10/DEC-020 no protocolo e a seção DEC-020 desta página descrevem IC de kappa por bootstrap de casos; DEC-022 aprova bootstrap por componente.
- DEC-019 descreve clusters por artigo/`bundle:`; DEC-023 acrescenta a união transitiva de todos os artigos citados como unidade final de reamostragem/permutação.

A aprovação documental de DEC-021–DEC-023 declarou expressamente que não altera o pré-registro nem o protocolo. Portanto, este registro não reescreve esses artefatos protegidos nem presume que o conflito esteja resolvido. Uma emenda datada e uma reconciliação explícita entre pré-registro, protocolo, estatísticas, executor e testes são necessárias antes de qualquer avaliação confirmatória. Até lá, não executar H1 nem calcular concordância humana sob a nova especificação.
