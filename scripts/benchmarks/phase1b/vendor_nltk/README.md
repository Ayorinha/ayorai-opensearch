# Vendored NLTK 3.9.4 segmentation

`sent_tokenize` and `word_tokenize` exactly as in nltk 3.9.4, for the Phase 1b inference
jobs only (`run_shard.py`, protocols MiniCheck and FactCG). Licensed under the Apache
License 2.0 (`LICENSE.txt`, copied from the nltk 3.9.4 wheel). Copyright 2001-2026 NLTK
Project; authors as listed in each file header.

**Why.** nltk 3.9.4 has 31 published high/critical advisories, all outside these two
functions, and nltk 3.10.4 segments differently, which would change the DEV scores
(`docs/audit/P4-NLTK-EQUIVALENCE-2026-11-28.md`). Vendoring keeps the historical
segmentation while the job that holds the artifact key installs no nltk at all.

**Source.** Official wheel `nltk-3.9.4-py3-none-any.whl` from PyPI. Upstream file hashes
from its `RECORD`:

| upstream file | sha256 (urlsafe base64, as in RECORD) |
|---|---|
| `nltk/tokenize/punkt.py` | `SsUx2cvVV9XBb3TIG7olW1pS58UYLRfD5gIxtXpJSPM` |
| `nltk/tokenize/destructive.py` | `0NUsnfdiMo80rqT7loK0slPF994iiFsyBhcjkEJ2jN8` |
| `LICENSE.txt` | `z8d0m5b2O9McPEK1xHG_dWgUBT6EfBDz6wA0F7xSPTA` |

**Edits (everything else is upstream text):**
- `punkt.py`: provenance banner; `FreqDist` and `nltk.tokenize.api` imports replaced by
  `._api.TokenizerI`; the `PunktTrainer` section (upstream lines 632-1235) removed, so
  `PunktSentenceTokenizer.train` raises for text input; `PunktTokenizer` and
  `load_punkt_params` (upstream lines 1739-1777) rewritten to read a `punkt_tab/<lang>`
  directory with the same parsing as `nltk.tabdata.PunktDecoder`; save and demo helpers
  removed.
- `destructive.py`: provenance banner; `nltk.tokenize.api` and `nltk.tokenize.util`
  imports replaced by `._api.TokenizerI`; `NLTKWordTokenizer.span_tokenize` removed.
- `__init__.py`: `sent_tokenize` and `word_tokenize` as in `nltk/tokenize/__init__.py`,
  with the punkt_tab directory set by `configure(data_dir)` instead of `nltk.data.path`.
- `_api.py`: minimal `TokenizerI`.

**Proof of equivalence.** `scripts/benchmarks/phase1b/nltk_equivalence.py` compares this
package with the official nltk 3.9.4 on 25,185 texts (no benchmark data): zero
differences in sentences, words and words per sentence, on Python 3.12 and 3.13. CI
checks every pull request against `tests/fixtures/phase1b_nltk394_segmentation.json`,
the nltk 3.9.4 reference on the fixed corpus (20,028 texts).
