# P4-01 — Equivalência de segmentação NLTK 3.9.4 × 3.10.4 (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

## Pergunta

O mantenedor autorizou atualizar o `nltk` de 3.9.4 para 3.10.4, versão que corrige os alertas apontados pelo `dependency-review`. A condição era um teste reprodutível mostrar segmentação idêntica à da versão histórica. Sem essa prova, a atualização não seria integrada.

## Método

- **Funções comparadas:** as duas que os shards da Phase 1b usam (`run_shard._document_chunks`):
  - `sent_tokenize`;
  - `word_tokenize`, mais a contagem de palavras por sentença que o protocolo FactCG usa.
- **Dados de segmentação:** `punkt_tab` fixado (`configs/benchmarks/nltk-punkt-tab-pin.json`, commit `550b6625`), com SHA-256 conferido por `nltk_resources.py`.
- **Corpus:** determinístico, **sem dado de benchmark** (nem DEV, nem TEST):
  - 28 casos de borda escritos à mão;
  - 5.139 textos de prosa do próprio repositório (README, CHANGELOG e `docs/**/*.md`, documentos inteiros e parágrafos), no estado do commit `a9bc72d5`;
  - 20.000 textos sintéticos com semente `20261128`, construídos com abreviações, decimais, aspas, apóstrofos, parênteses, reticências, quebras de linha e pontuação Unicode.
- **Execução:** `scripts/benchmarks/phase1b/nltk_equivalence.py`, uma vez em cada ambiente isolado (Python 3.12, nltk instalado do PyPI), e `--compare` sobre os dois relatórios.
- **Corpus idêntico nas duas execuções:** `corpus_sha256` `010a5d39…227d5`, 25.167 textos.

## Resultado [FATO]

| função | SHA-256 dos resultados, 3.9.4 | SHA-256 dos resultados, 3.10.4 | textos diferentes |
|---|---|---|---|
| `sent_tokenize` | `e2302b83…53ee` | `413f5e07…9c4a` | **5.997** (5.980 sintéticos, 17 do repositório) |
| `word_tokenize` | `d11e9928…98ef` | `a9d3c64e…9f86` | **11.915** (11.874 sintéticos, 34 do repositório, 7 de borda) |
| palavras por sentença | `519b3a50…de81` | `102211e1…6d26` | **10.507** |

**Exemplos:**

| texto | 3.9.4 | 3.10.4 |
|---|---|---|
| `Approx. »` | `["Approx.", "»"]` | `["Approx. »"]` |
| `Ação etc.! ’` | `["Ação etc.!", "’"]` | `["Ação etc.! ’"]` |
| `'Hello,' she said.` (palavras) | `'Hello`, `,`, `'` … | `'`, `Hello`, `,`, `'` … |
| `a 'b' c 'de' f 'ghi' j` (palavras) | 11 tokens | 13 tokens |

**Causas no código-fonte:**
- `tokenize/destructive.py` mudou a regra de aspas simples antes de palavras: `(\')(?!re|ve|ll|m|t|s|d|n)(\w)\b` passou a ser `(?<!\w)(\')(?!(?:re|ve|ll|m|t|s|d|n)\b)(?=\w)`. A aspa passa a ser um token separado.
- `tokenize/punkt.py` mudou o tratamento de aspas de fechamento Unicode depois do fim de sentença.

## Conclusão

**A equivalência não foi comprovada.** As duas versões segmentam de forma diferente em textos comuns, inclusive em prosa real em português e inglês. Pela condição do mantenedor, **a atualização para 3.10.4 não é integrada.** O lock de inferência mantém o nltk 3.9.4.

Consequência: com 3.10.4, os chunks dos protocolos MiniCheck e FactCG mudariam, e os escores DEV deixariam de reproduzir os históricos. Isso é uma mudança metodológica, não de engenharia.

## Reprodução

```
python -m venv /tmp/a && /tmp/a/bin/pip install nltk==3.9.4
python -m venv /tmp/b && /tmp/b/bin/pip install nltk==3.10.4
/tmp/a/bin/python scripts/benchmarks/phase1b/nltk_resources.py --data-dir /tmp/punkt
/tmp/a/bin/python -I scripts/benchmarks/phase1b/nltk_equivalence.py --data-dir /tmp/punkt --output /tmp/a.json
/tmp/b/bin/python -I scripts/benchmarks/phase1b/nltk_equivalence.py --data-dir /tmp/punkt --output /tmp/b.json
python scripts/benchmarks/phase1b/nltk_equivalence.py --compare /tmp/a.json /tmp/b.json  # sai com 1
```

A parte de prosa do repositório depende do commit. Para obter o mesmo `corpus_sha256`, execute no commit `a9bc72d5`.

## Desfecho: segmentação 3.9.4 embutida (2026-11-28)

Nem a atualização (que muda a segmentação) nem a aceitação do risco (que enfraqueceria o `dependency-review`) atendiam às restrições. A saída foi embutir só o código das duas funções da 3.9.4 (`scripts/benchmarks/phase1b/vendor_nltk/`, Apache-2.0, edições listadas no README do pacote). O job `shard` deixa de instalar o nltk.

**Equivalência do pacote embutido com o nltk 3.9.4 oficial [FATO]:**

| corpus | textos | `sent_tokenize` | `word_tokenize` | palavras por sentença |
|---|---|---|---|---|
| completo (com a prosa do repositório) | 25.185 | 0 diferenças | 0 diferenças | 0 diferenças |
| fixo (borda + sintéticos) | 20.028 | 0 diferenças | 0 diferenças | 0 diferenças |

- **Ambientes:** Python 3.12.3 e 3.13.18.
- **Referência fixa:** `tests/fixtures/phase1b_nltk394_segmentation.json`, produzida com o nltk 3.9.4 oficial:
  - `corpus_sha256` `674fc993…d22f`;
  - `sent_tokenize` `01b6ffab…a237`.
- **CI:** o job `phase1b-inference-lock` instala o ambiente de inferência travado, confirma que o nltk não está instalado, baixa o `punkt_tab` fixado com SHA-256 conferido e exige a mesma referência.
