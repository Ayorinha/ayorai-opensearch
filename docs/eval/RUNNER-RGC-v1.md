# [PROPOSTO] Executor de avaliação do benchmark RGC (v1)

**Estado:** [PROPOSTO] — aguarda congelamento pelo mantenedor  
**Data:** 2026-10-13  
**Responsável:** Anderson Leon Ayora  
**Código:** `evals/ptbr/rgc_eval.py` · **Testes:** `tests/test_rgc_eval_runner.py`  
**Relação:** complementa `docs/eval/PREREGISTRATION-RGC-v1.md` (métricas e critérios) e `docs/eval/PROTOCOL-GOLDEN-V1.md` (anotação).

Este documento fixa **como** o sistema será executado sobre os casos do RGC, antes de qualquer execução sobre casos reais. O executor foi testado apenas com documentos e casos **sintéticos**. Nenhum caso do piloto ou do benchmark foi executado.

## 1. Salvaguardas

- O subcomando `run` exige um arquivo de rótulos humanos completo (`--labels`). Não existe modo "só previsões"; por isso o sistema não pode ser rodado sobre casos ainda não rotulados, evitando que a saída do sistema influencie a anotação.
- Casos sem rótulo, rótulos de casos inexistentes e casos duplicados interrompem a execução (erro), em vez de serem descartados em silêncio.
- Rótulo `RULE_GAP` (lacuna nas regras de anotação, usado somente no piloto) remove o caso do denominador e é sempre listado em `excluded` no relatório; no conjunto definitivo, `RULE_GAP` é proibido no campo `label`.
- **DEC-017 (Opção A aprovada em 2026-10-21; Emenda 7):** o executor interrompe a execução diante de registro ausente/duplicado, ID desconhecido, rótulo humano ausente ou arquivo inconsistente; uma predição presente não mapeável para `judge2` recebe `INVALID_PREDICTION`, permanece no denominador e conta como erro. A aprovação não autoriza avaliação confirmatória e não congela o protocolo.
- O relatório registra: versão do executor, commit, versão do Python, SHA-256 dos casos, dos rótulos e dos documentos, configuração completa, cada previsão com o `output_sha256` do Judge e a contagem de previsões cujo estado original do Judge foi `ABSTAINED`.

## 2. Pipeline por caso (determinístico, sem rede, sem componente aprendido)

1. **Evidência**
   - **Modo `oracle`**: usa os trechos do próprio caso (`evidence[].excerpt`), conferidos caractere a caractere contra o texto do documento nos offsets declarados. Mede stance + Judge isoladamente, sem recuperação.
   - **Modo `retrieval`**: o texto de `DOCUMENTS.jsonl` é segmentado em dispositivos e os *k* melhores trechos são recuperados por BM25 (§3). Mede o sistema de ponta a ponta.
2. **Stance**: `RuleStanceDetector` (versão registrada no relatório) para cada par (afirmação, trecho).
3. **Veredito**: Judge 2.0 `adjudicate` (ADR-009). Afirmação simples: **um átomo** cobrindo a afirmação inteira. Afirmação composta (DEC-010, opção A): os átomos anotados no campo `atoms` do caso (dois ou mais trechos da afirmação, por `start_offset`/`end_offset`, ordenados e sem sobreposição); a posição é detectada por átomo contra cada trecho, e o veredito composto segue K1–K5. Anotação de átomos inválida interrompe a execução.
4. **Estrato retificado** (Emenda 4, DEC-011 opção A; executor `rgc-eval/0.5.0`): o campo opcional `rectified` do caso deve ser booleano (`true`/`false`); ausência equivale a `false` e qualquer outro valor interrompe a execução. Casos retificados **permanecem** nas métricas primárias e também são reportados em `strata.rectified`; os demais em `strata.not_rectified`. Cada estrato traz `n`, contagens de referência, acurácia, acurácia balanceada, macro-F1, IC95% por bootstrap e matriz de confusão; nenhum critério H1 é decidido por estrato. A marca não entra no Judge: o `output_sha256` de cada caso é idêntico com ou sem o campo.
5. **Mapeamento** (`to_label`): `DECIDED` → veredito do Judge; `ABSTAINED` → `UNVERIFIED` (DEC-009 aprovada); qualquer outro estado → `INVALID_PREDICTION`. No vocabulário histórico `adr002`, `SUPPORTED` com robustez `R3` → `VERIFIED` (ADR-009 §11), mas esse mapeamento não se aplica ao vocabulário RGC `judge2`.

## 3. Parâmetros propostos para congelamento

| Parâmetro | Valor proposto | Observação |
|---|---|---|
| Modo da avaliação principal | `retrieval` | `oracle` reportado ao lado, como análise secundária |
| Segmentação | `dispositivo` (início de linha: `Art.`, `§`, `Parágrafo único`, incisos romanos `I -`, alíneas `a)`) | alternativa `artigo` disponível só para análise secundária |
| Recuperação | BM25, `k1 = 1,2`, `b = 0,75`, top-*k* = 3 | empate desfeito pela ordem no corpus |
| Tokenização | `\w+` em minúsculas; mantém números; remove tokens com menos de 3 letras e uma lista fixa de palavras funcionais | nenhuma palavra do domínio na lista |
| Vocabulário | `judge2` (5 estados) | DEC-007 aprovada (5 estados); `adr002` (6 estados) permanece apenas como vocabulário histórico alternativo, não usado no RGC |
| Macro-F1 | média sobre a união dos estados de referência e previstos, **incluindo** `INVALID_PREDICTION` (F1 = 0, escolha conservadora) | |
| Acurácia balanceada | média das revocações dos estados presentes na referência | |
| IC95% primário | bootstrap percentil por cluster de artigo, 10.000 reamostragens, seed `20261003`; casos multiartigo usam `bootstrap_cluster_id` canônico conforme DEC-019/Emenda 9 | DEC-019; `docs/eval/STATISTICS.md` |
| IC95% de sensibilidade | bootstrap percentil por caso, 10.000 reamostragens, seed `20261003` | Reportar separadamente do intervalo primário por cluster |
| Baseline B primária | classe majoritária dos rótulos humanos da partição pública de desenvolvimento (70%); aplicada sem alteração à avaliação; empate resolvido pela ordem fixa de `VOCABULARIES["judge2"]` | DEC-014/Emenda 6; `majority_label` em `evals/ptbr/rgc_eval.py`; registrar rótulos, contagens e SHA-256 no relatório |
| Baseline A descritiva | classe majoritária da própria partição avaliada; empate desfeito pela ordem do vocabulário | somente prevalência observada; excluída de H1 |
| Comparação | McNemar exato bilateral (`ayorai_attractor.evaluation.stats`) | |
| Precisão das decisões | as três condições de H1 usam valores **não arredondados**; o arredondamento (6 casas) vale só para o relatório | |

Depois de congelados, qualquer mudança nesses valores exige emenda datada antes de nova execução, conforme o pré-registro §5.

## 4. Exportação do corpus estrito

`python evals/ptbr/rgc_eval.py export-corpus --out <arquivo>` gera o corpus com exatamente os 5 campos aceitos por `scripts/check_golden_pt.py --corpus` (`source_id`, `source_url`, `source_license`, `retrieved_at`, `text`). O teste confirma que o validador aceita a exportação sem erros.

## 5. Limitações conhecidas (declaradas antes dos dados)

- **Átomos anotados, não decompostos automaticamente:** o executor não divide afirmações por conta própria. Sem o campo `atoms`, a afirmação é um único átomo e, pelas regras A1–A4, só pode resultar em `SUPPORTED`, `REFUTED`, `CONFLICTING` ou `UNVERIFIED`. `PARTIALLY_SUPPORTED` (regra K4) só é alcançável quando o caso traz dois ou mais átomos anotados. Por isso, todo caso de referência rotulado `PARTIALLY_SUPPORTED` deve trazer os átomos; a regra de anotação está na Emenda 3 do protocolo (PR #205, mesclada em 2026-10-16). Casos sem `atoms` produzem exatamente o mesmo resultado e o mesmo `output_sha256` da versão anterior do executor. Esta descrição e o executor permanecem **[PROPOSTO]**.
- **Stance lexical:** o `RuleStanceDetector` compara números, datas e sobreposição de palavras; paráfrases fortes e negações implícitas tendem a sair como `NEUTRAL` → `UNVERIFIED`.
- **Dispositivo sem o caput:** um inciso recuperado isoladamente não carrega o texto do caput do artigo.
- **Ruído do DOU:** cabeçalhos e rodapés de página extraídos pelo `pdftotext` ficam anexados ao dispositivo anterior.
- **Uma única origem:** todos os trechos vêm do mesmo ato normativo, portanto a robustez máxima esperada é limitada (`VERIFIED` exige R3 no vocabulário `adr002`).
- **`canonical_url` omitido:** o executor não preenche `canonical_url` nas evidências (a URL fica em `source_location`). Ver §6.

## 6. Achado durante a implementação (fora do escopo deste executor)

Uma requisição `r2-a` válida com `evidence[].canonical_url` preenchido retornava `INVALID_INPUT / SCHEMA_VIOLATION` em vez de ser adjudicada (issue #182). A correção, com testes de regressão, foi mesclada pelo mantenedor na [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) em 2026-10-15. O executor continua sem preencher `canonical_url` (§5); essa escolha não depende mais do defeito.

## 7. Uso (somente após rótulos completos e parâmetros congelados)

```bash
python evals/ptbr/rgc_eval.py run <casos-avaliacao.jsonl> \
    --labels <rotulos-avaliacao.jsonl> \
    --development-cases <casos-desenvolvimento-publico.jsonl> \
    --development-labels <rotulos-desenvolvimento-publico.jsonl> \
    --partition hidden --mode retrieval --out reports/rgc-<data>.json
```

Formato dos rótulos (um por linha): `{"case_id": "...", "verdict": "SUPPORTED"}`.

A execução exige a partição pública de desenvolvimento por `--development-cases` e seus rótulos humanos completos por `--development-labels`. O argumento obrigatório `--partition` declara a partição do arquivo de avaliação: `hidden` habilita o critério confirmatório de H1; `development` calcula somente métricas descritivas e marca H1 como não testada. O executor valida que os IDs dos dois arquivos correspondem exatamente, deriva B somente desses rótulos, registra os SHA-256 dos casos e rótulos e recusa IDs sobrepostos entre desenvolvimento e avaliação. A baseline A, derivada dos rótulos de avaliação, aparece separadamente como descritiva e não participa de H1.

Este executor não afirma validação, parceria ou endosso da Anatel ou de qualquer instituição.


## DEC-019 — agrupamento do bootstrap por artigo

Para cada caso elegível na partição oculta, `bootstrap_cluster_id` deve ser uma string não vazia e estável. Use o ID canônico do artigo que contém a regra principal que decide a afirmação. Se a afirmação depender conjuntamente de vários artigos sem um principal único, use `bundle:` seguido dos IDs canônicos únicos ordenados lexicalmente e unidos por `+`. `cited_article_ids` preserva a lista completa de artigos citados quando aplicável. Casos com a mesma chave são reamostrados juntos; bundles são clusters próprios. A execução confirmatória interrompe se o campo estiver ausente ou inválido.

O relatório publica `system_ci95` como intervalo primário por cluster de artigo e `system_ci95_case_bootstrap` como sensibilidade por caso, além do número de clusters e da unidade de reamostragem. Ambos usam 10.000 iterações e seed `20261003`. Nenhum bootstrap real ou métrica RGC foi produzido por esta alteração.


**Nota de consistência (2026-10-21):** DEC-017 e DEC-018 estão aprovadas pelo mantenedor (opção A); as propostas históricas correspondentes não representam estado pendente. O protocolo permanece **[PROPOSTO]** e não congelado.
