# ATTRACTOR Model License Policy

Status: Accepted for F1
Verification date: 2026-10-03

## Scope

ATTRACTOR does not package or redistribute model weights. The user selects the backend by configuration and downloads the selected artifacts themselves.

This is a repository governance policy, not legal advice.

## License levels

### COMMERCIAL_DEFAULT

A model is eligible only when its weights use Apache-2.0, MIT, or CC BY 4.0; every declared training dataset is identified; no declared training dataset has NC terms; and the available evidence is sufficient to reproduce the determination. Permissive and share-alike datasets are accepted with the associated compliance risk documented.

### EVAL_ONLY

A model is evaluation-only when declared training data includes NC terms, or when the available license evidence is insufficient for COMMERCIAL_DEFAULT.

EVAL_ONLY backends may be used only for evaluation and comparison. Code rejects them outside evaluation mode unless the caller supplies an explicit opt-in. The evaluation mode or opt-in is recorded in backend provenance. An EVAL_ONLY model never silently becomes the default.

## Required model record

Every registered model records: model ID, immutable revision, weight license, training datasets and revisions where available, license of every declared dataset, assigned level, verification date, and evidence sources.

## F1 registry

### A — multilingual direct NLI

Model: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
Revision: b5113eb38ab63efdd7f280f8c144ea8b13f978ce
Weights: MIT
Training data: includes XNLI, MultiNLI, ANLI and other NLI datasets
Level: EVAL_ONLY
Reason: the relevant XNLI licensing record carries CC BY-NC 4.0 terms.
F1 use: evaluation and comparison only.

### B — translate-then-verify

English NLI candidate:
cross-encoder/nli-deberta-v3-base
Revision checked: 6c749ce3425cd33b46d187e45b92bbf96ee12ec7
Weights: Apache-2.0
Declared training datasets: MultiNLI and SNLI
MultiNLI declares permissive/share-alike components; SNLI is CC BY-SA 4.0. No declared NC dataset was found for this NLI component.

PT to EN translation candidate:
Helsinki-NLP/opus-mt-ROMANCE-en
Weights: Apache-2.0
Training data is declared as OPUS, but the model card does not provide an immutable, per-source license inventory for the OPUS material used by this checkpoint.

F1 decision: B is BLOCKED. The missing per-source OPUS license inventory prevents a defensible COMMERCIAL_DEFAULT determination. No commercial right is inferred from the translation weight license alone.

## Current default

No EVAL_ONLY model is a commercial default. F1 measures A explicitly in evaluation mode and keeps C, rules-only, as the reference ablation.

This policy is not legal advice; review by an intellectual-property specialist is recommended before commercial use.
