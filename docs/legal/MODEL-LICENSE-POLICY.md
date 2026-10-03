# ATTRACTOR Model License Policy

Status: normative F1 policy
Verified: 2026-10-03

## Scope

ATTRACTOR does not package or redistribute model weights. The user selects a backend by configuration and downloads the selected model.

## License levels

### COMMERCIAL_DEFAULT

A model is eligible only when:

- the weights have Apache-2.0, MIT or CC BY 4.0;
- no declared training data is under non-commercial (NC) terms;
- permissive and share-alike training-data licenses are accepted with the risk documented.

### EVAL_ONLY

A model is EVAL_ONLY when its declared training includes NC data, or when the project deliberately restricts the model to non-commercial evaluation.

The runtime rejects an EVAL_ONLY backend outside evaluation mode unless the user supplies an explicit license opt-in. That opt-in is recorded in provenance.

## F1 registry

| Component | Model | Revision | Weights | Declared training data | License assessment | Level | Verified |
|---|---|---|---|---|---|---|---|
| A NLI | MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 | b5113eb38ab63efdd7f280f8c144ea8b13f978ce | MIT | ANLI; XNLI; MultiNLI; other declared corpora | XNLI is CC BY-NC 4.0 | EVAL_ONLY | 2026-10-03 |
| B translation | Helsinki-NLP/opus-mt-ROMANCE-en | ddfee805aaa57f4bd198f88e8832ba2b012f9ae2 | Apache-2.0 | OPUS | Source-license chain is not treated as commercial clearance | EVAL_ONLY | 2026-10-03 |
| B NLI | cross-encoder/nli-deberta-v3-base | dcaec5ddc7a9456405d53c33bb2d4050ca4f75cf | Apache-2.0 | SNLI; MultiNLI | No NC term identified in declared metadata; B remains non-commercial by project policy | EVAL_ONLY | 2026-10-03 |

B is measurable but is not a COMMERCIAL_DEFAULT and must not be selected as the production default.

## Runtime enforcement

The optional NLI backend has a license guard. EVAL_ONLY backends are rejected unless evaluation mode or an explicit opt-in is active. Provenance records the gate state.

## Legal notice

This policy is not legal advice; review by an intellectual-property specialist is recommended before commercial use.
