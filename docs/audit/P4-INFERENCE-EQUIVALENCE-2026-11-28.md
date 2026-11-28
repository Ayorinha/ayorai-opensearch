# P4-01 — Equivalência de escores do ambiente de inferência (2026-11-28)

Revisão por ferramenta automatizada, publicada pelo mantenedor.

| item | valor |
|---|---|
| Ambiente histórico | torch 2.7.1+cpu, transformers 4.55.4 (lock `cf052d1f…` na branch preservada `0edc35b9`) |
| Ambiente adotado | torch 2.14.0+cpu, transformers 5.24.0 (`requirements-phase1b-torch-cpu.txt`, `requirements-phase1b-inference.txt`) |
| Critério | mesma divisão em blocos, \|Δescore\| ≤ 1e-5 e nenhuma decisão trocada em 0,5, nos três modelos |
| Workflow | `.github/workflows/phase1b-inference-equivalence.yml` |
| Dados | 90 pares sintéticos determinísticos (30 documentos de 1, 5 e 20 frases × 3 tipos de afirmação). Nenhum dado DEV ou TEST |

**Rótulos:**
- **[FATO]**: verificado por execução;
- **[HIPÓTESE]**: não verificado.

Teste de software não é validação científica. A equivalência é medida em texto sintético, que exercita os caminhos de segmentação, divisão em blocos, truncamento e lote, não a distribuição do DEV.

## 1. Por que trocar [FATO]

- `torch` 2.7.1 tem alertas altos corrigidos entre 2.8 e 2.13, inclusive execução de código ao carregar checkpoint (`GHSA-63cw-57p8-fm3p`). O MiniCheck é carregado de `pytorch_model.bin`.
- `transformers` 4.55.4 tem alertas altos corrigidos só na série 5.x.
- O job `shard` recebe a chave de artefato e decifra o DEV.

## 2. Primeira medição: não equivalente [FATO]

Execução `46178535233` (commit `c12db9a6`), código do shard sem mudança:

| modelo | max \|Δ\| | decisões trocadas | mesma divisão |
|---|---|---|---|
| mDeBERTa | 0,1938 | 3 | não |
| MiniCheck | 0,1177 | 0 | não |
| FactCG | 0,1228 | 0 | sim |

Pelo critério, a troca não foi integrada nessa forma.

## 3. Localização: um pacote por vez [FATO]

Execução `46179916443` (commit `79df25fd`):

| ambiente | mDeBERTa | MiniCheck | FactCG | resultado |
|---|---|---|---|---|
| só torch 2.14 (transformers 4.55.4) | 2,26e-6 | 8,05e-7 | 1,31e-6 | equivalente |
| só transformers 5.24 (torch 2.7.1) | 0,1938, 3 trocas | 0,1177 | 0,1228 | não equivalente |

A diferença vem inteira do transformers 5.x.

## 4. Causa [FATO]

- Os três modelos usam o tokenizador DeBERTa-v2. Cada revisão fixada traz `tokenizer.json` e `spm.model`.
- No 4.55.4, `AutoTokenizer` carrega `DebertaV2TokenizerFast` a partir do `tokenizer.json`.
- No 5.24, `AutoTokenizer` devolve `DebertaV2Tokenizer` reconstruído a partir do `spm.model`. Alguns trechos viram `[UNK]` (id 3): 27 de 30 documentos codificam diferente.
- No FactCG a contagem de tokens coincidia por acaso, mas os ids não.
- O 5.x também deixou de devolver `token_type_ids` por padrão. Os três modelos têm `type_vocab_size` 0 e os ignoram.

## 5. Correção [FATO]

`scripts/benchmarks/phase1b/run_shard.py`:
- `load_pinned_tokenizer` lê o `tokenizer.json` da revisão fixada com `PreTrainedTokenizerFast`. Recusa a revisão que não tiver esse arquivo.
- `token_type_ids` é pedido explicitamente nas duas formas de entrada.

Nada no protocolo muda: o modelo, a revisão, o arquivo de tokenizador, a segmentação, os blocos, o truncamento e o limiar são os mesmos.

**Conferência local dos tokenizadores** (só os arquivos de tokenizador das três revisões, os 90 pares):
- 4.55.4 com `AutoTokenizer` (referência) e 4.55.4 com `PreTrainedTokenizerFast`: idênticos;
- 4.55.4 (referência) e 5.24.0 com `PreTrainedTokenizerFast`: idênticos;
- campos comparados: `input_ids`, `attention_mask` e `token_type_ids`, em par documento/afirmação e em texto único, além de `encode` sem tokens especiais.

## 6. Medição final: equivalente [FATO]

Execução `46181650820` (commit `fdcf82f2`), job `phase1b-inference-equivalence` verde:

| comparação com o histórico | mDeBERTa | MiniCheck | FactCG | trocas | mesma divisão |
|---|---|---|---|---|---|
| torch 2.14 + transformers 5.24 (adotado) | 2,56e-6 | 8,34e-7 | 1,37e-6 | 0 | sim |
| só torch 2.14 | 2,56e-6 | 2,62e-6 | 1,37e-6 | 0 | sim |
| só transformers 5.24 | 2,09e-6 | 0 | 0 | 0 | sim |

Todas as diferenças ficam abaixo de 1e-5, ruído de ponto flutuante em fp32.

**Ressalva:** a partir dessa execução o ambiente histórico também roda o código corrigido. Isso é válido porque, no 4.55.4, o tokenizador lido do `tokenizer.json` codifica igual ao `AutoTokenizer` (seção 5).

## 7. O que continua valendo

- O workflow roda a cada PR que muda os locks, o shard, os protocolos ou a segmentação embutida.
- Os ambientes intermediários só informam; o que bloqueia é a comparação do ambiente adotado com o histórico.
- Antes de qualquer número novo de acurácia, a execução DEV completa continua dependendo de autorização do mantenedor e da chave gold.
