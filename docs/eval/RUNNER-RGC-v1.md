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
- Previsões inválidas (`INVALID_PREDICTION`) permanecem no denominador e contam como erro, conforme o pré-registro §4.
- O relatório registra: versão do executor, commit, versão do Python, SHA-256 dos casos, dos rótulos e dos documentos, configuração completa, cada previsão com o `output_sha256` do Judge e a contagem de previsões cujo estado original do Judge foi `ABSTAINED`.

## 2. Pipeline por caso (determinístico, sem rede, sem componente aprendido)

1. **Evidência**
   - **Modo `oracle`**: usa os trechos do próprio caso (`evidence[].excerpt`), conferidos caractere a caractere contra o texto do documento nos offsets declarados. Mede stance + Judge isoladamente, sem recuperação.
   - **Modo `retrieval`**: o texto de `DOCUMENTS.jsonl` é segmentado em dispositivos e os *k* melhores trechos são recuperados por BM25 (§3). Mede o sistema de ponta a ponta.
2. **Stance**: `RuleStanceDetector` (versão registrada no relatório) para cada par (afirmação, trecho).
3. **Veredito**: Judge 2.0 `adjudicate` (ADR-009), com **um átomo** cobrindo a afirmação inteira.
4. **Mapeamento** (`to_label`): `DECIDED` → veredito do Judge; `ABSTAINED` → `UNVERIFIED` (DEC-009 aprovada); qualquer outro estado → `INVALID_PREDICTION`. No vocabulário histórico `adr002`, `SUPPORTED` com robustez `R3` → `VERIFIED` (ADR-009 §11), mas esse mapeamento não se aplica ao vocabulário RGC `judge2`.

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
| IC95% | bootstrap percentil, 10.000 reamostragens, seed `20261003`, mesma sequência de reamostragem para as três métricas | |
| Baseline | classe majoritária da partição avaliada; empate desfeito pela ordem do vocabulário | |
| Comparação | McNemar exato bilateral (`ayorai_attractor.evaluation.stats`) | |
| Precisão das decisões | as três condições de H1 usam valores **não arredondados**; o arredondamento (6 casas) vale só para o relatório | |

Depois de congelados, qualquer mudança nesses valores exige emenda datada antes de nova execução, conforme o pré-registro §5.

## 4. Exportação do corpus estrito

`python evals/ptbr/rgc_eval.py export-corpus --out <arquivo>` gera o corpus com exatamente os 5 campos aceitos por `scripts/check_golden_pt.py --corpus` (`source_id`, `source_url`, `source_license`, `retrieved_at`, `text`). O teste confirma que o validador aceita a exportação sem erros.

## 5. Limitações conhecidas (declaradas antes dos dados)

- **Um átomo por afirmação:** o executor atual passa a afirmação inteira como um único átomo. Pelas regras atômicas A1–A4 de `rules/judge-2.0.0.json`, um único átomo pode resultar apenas em `SUPPORTED`, `REFUTED`, `CONFLICTING` ou `UNVERIFIED`. A regra K4 exige dois ou mais átomos para `PARTIALLY_SUPPORTED`; portanto, o executor atual não prevê `PARTIALLY_SUPPORTED`, e casos de referência com esse rótulo contariam como erro estrutural. `CONFLICTING` continua possível pela regra A4. A correção dessa limitação depende da decisão DEC-010, ainda pendente. Esta descrição e o executor permanecem **[PROPOSTO]**.
- **Stance lexical:** o `RuleStanceDetector` compara números, datas e sobreposição de palavras; paráfrases fortes e negações implícitas tendem a sair como `NEUTRAL` → `UNVERIFIED`.
- **Dispositivo sem o caput:** um inciso recuperado isoladamente não carrega o texto do caput do artigo.
- **Ruído do DOU:** cabeçalhos e rodapés de página extraídos pelo `pdftotext` ficam anexados ao dispositivo anterior.
- **Uma única origem:** todos os trechos vêm do mesmo ato normativo, portanto a robustez máxima esperada é limitada (`VERIFIED` exige R3 no vocabulário `adr002`).
- **`canonical_url` omitido:** o executor não preenche `canonical_url` nas evidências (a URL fica em `source_location`). Ver §6.

## 6. Achado durante a implementação (fora do escopo deste executor)

Uma requisição `r2-a` válida com `evidence[].canonical_url` preenchido retorna `INVALID_INPUT / SCHEMA_VIOLATION` em vez de ser adjudicada. A causa e a correção estão em revisão na PR #192; até que ela seja mesclada pelo mantenedor, não declarar o defeito corrigido nem presumir CI verde. A PR documenta a hipótese confirmada e os testes propostos: https://github.com/Ayorinha/ayorai-opensearch/pull/192.

## 7. Uso (somente após rótulos completos e parâmetros congelados)

```bash
python evals/ptbr/rgc_eval.py run <casos.jsonl> --labels <rotulos.jsonl> \
    --mode retrieval --out reports/rgc-<data>.json
```

Formato dos rótulos (um por linha): `{"case_id": "...", "verdict": "SUPPORTED"}`.

Este executor não afirma validação, parceria ou endosso da Anatel ou de qualquer instituição.
