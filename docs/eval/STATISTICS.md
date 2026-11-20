# Evaluation Statistics

ATTRACTOR keeps decision logic separate from statistical reporting.

- **6×6 confusion matrix:** fixed to the six ADR-002 Judge verdict states. This is a legacy/statistical contract for that vocabulary, not a universal matrix for every evaluation.
- **RGC PT-BR vocabulary:** the RGC executor uses the five `judge2` states defined by Judge 2.0. Its confusion matrix follows that vocabulary and the documented treatment of `INVALID_PREDICTION`; the legacy ADR-002 6×6 matrix must not be interpreted as the RGC label space.
- **Bootstrap:** the RGC runner reports deterministic percentile 95% confidence intervals for accuracy, balanced accuracy, and macro-F1, using 10,000 resamples and seed `20261003`. One shared resample sequence (an RGC-PRNG-1 stream, DEC-027 D3) is used for all three metrics. Limits are the Hyndman–Fan type 7 quantiles at `p = 1/40` and `39/40`, with `h = (n − 1)·p` computed exactly (DEC-027 D2). Before `rgc-eval/0.8.0` the runner used order statistics without interpolation and Python's `random.Random`; intervals from earlier versions are not numerically comparable.
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

**Atualização (2026-11-14, DEC-027 D5 / Emenda 11):** o intervalo primário de H1 passou a ser o bootstrap por componente conectado; o bootstrap por cluster de artigo descrito abaixo continua sendo calculado, agora como sensibilidade. Texto original: o intervalo de confiança primário para H1 usa reamostragem de clusters de artigo; o bootstrap por caso é uma análise de sensibilidade. O campo `bootstrap_cluster_id` é obrigatório nos casos elegíveis da partição oculta. Caso com artigo principal usa seu identificador canônico; caso dependente de múltiplos artigos sem principal único usa `bundle:` com IDs canônicos únicos em ordem lexical, separados por `+`. `cited_article_ids` mantém a lista completa de referências. A amostragem sorteia com reposição tantos clusters quantos clusters únicos existem, inclui todos os casos do cluster sorteado e preserva multiplicidade de sorteios. Publicar método, seed, iterações, número de clusters e os dois intervalos. Esta decisão não congela o protocolo nem autoriza avaliação RGC.


## Concordância entre anotadores — DEC-020 e DEC-022

DEC-020 estabelece Cohen's kappa não ponderado para os cinco rótulos nominais, gate pela estimativa pontual `κ ≥ 0,6`, concordância observada, matriz de confusão, marginais por classe e exclusão auditável de pares em que qualquer anotador usa `RULE_GAP`. A ferramenta deve interromper se os arquivos não tiverem IDs exatamente correspondentes ou contiverem duplicatas/rótulos inválidos.

**Atualização normativa (2026-11-07, DEC-022):** o IC95% de kappa aprovado para o RGC é bootstrap por componente conectado, com 10.000 reamostragens, fluxo `dec022-kappa-bootstrap` do RGC-PRNG-1 e quantil tipo 7. O bootstrap por caso descrito na Emenda 10 permanece no protocolo e na implementação atual de `evals/ptbr/rgc_agreement.py`, mas não substitui a especificação posterior da DEC-022. A rotina por componente existe em `rgc_components.py`; sua integração à ferramenta de concordância exige reconciliação datada da Emenda 10 no protocolo e pré-registro, seguida de revisão humana. Até lá, não usar a ferramenta atual como se já implementasse o IC vigente da DEC-022.

O esquema JSONL e os comandos estão no [guia de concordância entre anotadores](ANNOTATOR-AGREEMENT.md). Nenhum arquivo de anotação humana foi fornecido ou processado nesta execução.

## RGC PT-BR — decisões estatísticas por componentes (DEC-021 a DEC-023 e DEC-027)

**Estado:** DEC-021, DEC-022 e DEC-023 foram aprovadas em 2026-11-07. A DEC-027 (2026-11-14) especificou o que elas deixavam em aberto: IDs, gerador, percentil, validação e gate. A Emenda 11 do pré-registro (2026-11-14) levou o teste e o IC por componente para H1. **Protocolo [PROPOSTO]; nenhuma execução real autorizada; nenhum resultado RGC existe.**

**Superado (mantido no histórico do repositório):** uma versão anterior desta seção propunha `component:sha256:` + SHA-256 de JSON como ID de componente, NumPy `2.3.3` com `PCG64` e quantis por `numpy.quantile`. Essas escolhas não constavam das decisões aprovadas e foram substituídas pela DEC-027: ID literal da DEC-023, RGC-PRNG-1 e quantil tipo 7 definido por fórmula.

### Unidade final — DEC-023, com IDs da DEC-027 D1

1. Cada caso é um vértice. Dois casos pertencem ao mesmo componente quando compartilham ao menos um ID em `cited_article_ids`, com relação transitiva (`build_connected_article_components`, union-find iterativo).
2. IDs de artigo seguem a gramática da DEC-027 D1, implementada uma única vez em `evals/ptbr/rgc_ids.py`:
   - `[a-z0-9]+(-[a-z0-9]+)*(:[a-z0-9]+(-[a-z0-9]+)*)*`, no máximo 200 caracteres;
   - sem os prefixos reservados `bundle:` e `component:`; o `+` nunca ocorre num ID;
   - falha fechada: o validador recusa e nunca normaliza.
3. O ID do componente é o formato literal da DEC-023: `component:` + IDs únicos ordenados lexicalmente e unidos por `+`. Ele é inequívoco e reversível (`parse_component_id`).
4. O `bootstrap_cluster_id` da DEC-019 é obrigatório, canônico e citado na partição oculta (DEC-027 D6). A contagem de clusters antes da união nunca é parcial.
5. Reportar clusters antes da união, componentes depois da união, casos por componente e o maior componente.

### Gerador e percentil — DEC-027 D2 e D3

- **Sorteios.** Todos vêm do RGC-PRNG-1 (`evals/ptbr/rgc_random.py`), especificado byte a byte na DEC-027, com vetores de referência testados. Há um fluxo por procedimento:
  - `dec023-accuracy-bootstrap` (IC primário de acurácia);
  - `dec019-accuracy-bootstrap` e `case-accuracy-bootstrap` (sensibilidade);
  - `dec021-sign-flip`;
  - `dec022-kappa-bootstrap`;
  - `case-kappa-bootstrap`.
  As unidades são consumidas em ordem lexical dos IDs. `random.Random` e NumPy não são usados.
- **Limites dos IC95%.** Quantil tipo 7 de Hyndman–Fan com `h = (n − 1)·p` racional exato. Réplicas indefinidas são excluídas e contadas.

### Gate prévio de resolução — DEC-027 D7

- `evals/ptbr/rgc_gate.py` calcula `K` antes da anotação de veredito, a partir de um inventário JSONL com exatamente `case_id` e `cited_article_ids`.
- Recusa campos extras e chaves duplicadas, de modo que rótulos, previsões, resultados e `bootstrap_cluster_id` não entram no cálculo.
- O registro público contém só `K`, os tamanhos dos componentes e o maior componente.
**Limite de evidência do gate:** `rgc_gate.py` valida a estrutura do JSONL recebido (campos exatos, IDs, citações, duplicatas e grafo) e calcula `K`; ele não consegue provar, por si só, que o arquivo recebido contém o inventário completo do universo de casos elegíveis. A completude é uma precondição metodológica e deve ser atestada por responsável humano contra a fonte de cadastro/proveniência, antes da anotação, com o artefato privado de origem preservado e seu SHA-256 registrado. O registro público continua limitado a `K`, tamanhos dos componentes e maior componente. Nenhum inventário real foi fornecido, verificado ou calculado nesta revisão.

- Códigos de saída:
  - 0: `K ≥ 6`;
  - 3: `K < 6`;
  - 2: inventário inválido, vazio ou ausente, ou argumentos inválidos; nada é gravado.
- `K ≥ 6` é condição necessária, não suficiente: componentes em que o sistema e a Baseline B empatam (`d_k = 0`) não contam para a significância atingível (ver **Resolução**, abaixo).

### Teste de H1 — DEC-021 (Emenda 11)

- **Estatística.** Para cada componente `k`, `d_k = a_k − b_k`, em que `a_k` são os casos em que o sistema acerta e a Baseline B erra, e `b_k` o inverso (`component_differences`). `T_obs = Σ_k d_k`. Componentes com `d_k = 0` permanecem.
- **p-valor** (`sign_flip_by_component`):
  - `K ≤ 20`: enumeração das `2^K` combinações de sinais;
  - `K > 20`: 10.000 vetores de sinais do fluxo `dec021-sign-flip`, um sinal por componente na ordem dos IDs, com `p = (1 + E)/(1 + 10.000)`.
- **Resolução.** Componentes com `d_k = 0` não alteram nenhuma estatística permutada; o menor p exato atingível é `2/2^K′`, com `K′` = componentes com `d_k ≠ 0`. O relatório traz `K`, `K′` (`informative_component_count`), `minimum_attainable_p`, a resolução teórica da DEC-021 (`2/2^K`) e, no Monte Carlo, o p mínimo do estimador (`1/10.001`). Com `K′ < 6`, `significance_below_005_possible` é falso e H1 não pode receber suporte.
- **Sensibilidades, nunca substitutos:**
  - McNemar exato por caso (`mcnemar.role = sensitivity`);
  - teste de Obuchowski por componente (`obuchowski_sensitivity`), com `Var = K/(K−1)·Σ_k (x_k − y_k)²/N²` sob H0 e χ² com 1 grau de liberdade. A implementação reproduz o exemplo publicado PET/SPECT (21 clusters, variância 0,00484, χ² ≈ 2,857; 2,88 com as proporções arredondadas). Os dados do teste coincidem com o conjunto `thyroids` do pacote R [`clust.bin.pair`](https://cran.r-project.org/package=clust.bin.pair), cujos testes registram 2,86 (Durkalski et al., 2003) e 2,88 (Obuchowski, 1998). Referências: [Obuchowski, 1998, *Statistics in Medicine* 17(13):1495–1507](https://doi.org/10.1002/(SICI)1097-0258(19980715)17:13%3C1495::AID-SIM863%3E3.0.CO;2-I); [PubMed PMID 9695194](https://pubmed.ncbi.nlm.nih.gov/9695194/).
- **Hipótese de permutabilidade.** A validade do sign-flip depende da permutabilidade sistema/Baseline B dentro de cada componente sob H0. É uma hipótese metodológica: componentes por artigo não provam independência entre componentes.

### IC95% de acurácia de H1 — DEC-027 D5 (Emenda 11)

- **Primário.** Bootstrap percentil por componente (`bootstrap_metrics_by_component`, 10.000 réplicas, seed `20261003`), que preserva a multiplicidade dos componentes sorteados.
- **Sensibilidade.** Por cluster de artigo (`system_ci95_article_cluster`, DEC-019) e por caso (`system_ci95_case_bootstrap`).
- Os componentes do executor são construídos sobre os casos efetivamente avaliados. O gate D7, por sua vez, usa o inventário completo antes da anotação.

### IC95% de Cohen's kappa — DEC-022

- O bootstrap por componente (`bootstrap_cohen_kappa_by_component`) segue a DEC-022: 10.000 réplicas, fluxo `dec022-kappa-bootstrap` e quantil tipo 7. Réplicas indefinidas são excluídas e contadas; acima de 5%, o intervalo é **instável**.
- O gate continua na estimativa pontual `κ ≥ 0,6`.

### Bloqueios de coerência ainda abertos — revalidação 2026-11-19

- **Resolução informativa de H1:** a especificação acima exige que H1 não receba suporte quando `K′ < 6`. Na `main` consultada, `rgc_eval.py` calcula e registra `significance_below_005_possible`, mas a expressão final de `h1_supported` ainda não inclui esse indicador. A [PR #577](https://github.com/Ayorinha/ayorai-opensearch/pull/577), ainda Draft e não integrada, propõe exatamente essa barreira e uma regressão sintética para `K=25`, `K′=5` e p-valor Monte Carlo simulado abaixo de 0,05. Até sua integração autorizada, há divergência entre a regra de resolução e a decisão final implementada na main.
- **Reconciliação normativa de H1:** o pré-registro contém a Emenda 11, mas `docs/eval/PROTOCOL-GOLDEN-V1.md` ainda termina na Emenda 10. A DEC-027 exige emenda datada própria no protocolo. Esta atualização estatística não substitui essa emenda e não autoriza execução confirmatória.
- **Kappa por componente:** `rgc_components.py` contém a rotina de bootstrap por componente, mas `rgc_agreement.py` continua usando bootstrap por caso. A adoção da rotina pela ferramenta permanece bloqueada até a reconciliação datada da Emenda 10/DEC-022 e revisão humana; não processar anotações reais antes disso.

### Estado de implementação

- `evals/ptbr/rgc_eval.py` (`rgc-eval/0.12.0`, com captura E5 por snapshots imutáveis e avaliação em interpretador isolado, #580 e #584) implementa a validação D1/D6, os componentes, o IC primário por componente, o sign-flip primário e as sensibilidades. O executor recalcula o relatório de concordância a partir das anotações aprovadas antes de aceitá-lo.
- `evals/ptbr/rgc_agreement.py` ainda calcula o IC de kappa por bootstrap de casos (Emenda 10). Adotar o bootstrap por componente da DEC-022 na ferramenta de concordância é **pendência**: exige emenda datada da Emenda 10 (protocolo e pré-registro) e um inventário de citações dos casos anotados.
- Todos os testes usam IDs e dados sintéticos. Não há casos RGC reais, anotação humana processada nem estatística observada.

