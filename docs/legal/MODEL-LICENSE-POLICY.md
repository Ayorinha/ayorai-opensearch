# ATTRACTOR Model License Policy

Status: normative F1/F1.1 policy  
Verified: 2026-10-03

## Scope

ATTRACTOR does not package or redistribute model weights. The user selects a backend by configuration and downloads the selected model.

## Uniform eligibility rule

**COMMERCIAL_DEFAULT** requires all four conditions:

1. weights have an allowed permissive license: Apache-2.0, MIT or CC BY 4.0;
2. the model author has **not declared any NC (non-commercial) training dataset** in the model/dataset metadata reviewed;
3. the exact model revision is fixed;
4. the license/data assessment has a recorded verification date.

The absence of a public training-data inventory is **not itself evidence of an NC restriction**. It is recorded as an uncertainty/risk note. Conversely, a declared NC dataset is sufficient to make the model EVAL_ONLY.

Permissive and share-alike declared training-data licenses may be used with documented legal risk; they do not silently become NC.

**EVAL_ONLY** applies when:
- a declared training dataset is NC;
- licensing is explicitly restricted to non-commercial evaluation; or
- ATTRACTOR deliberately imposes a non-commercial restriction for the evaluation.

The runtime rejects EVAL_ONLY backends outside evaluation mode unless an explicit opt-in is supplied and recorded in provenance.

## F1/F1.1 registry

| Component | Model / family | Revision | Weights | Declared training data / evidence | Level | Verification |
|---|---|---|---|---|---|---|
| A NLI | MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 | b5113eb38ab63efdd7f280f8c144ea8b13f978ce | MIT | XNLI declared; XNLI is CC BY-NC 4.0 | EVAL_ONLY | 2026-10-03 |
| B translation | Helsinki-NLP/opus-mt-ROMANCE-en | ddfee805aaa57f4bd198f88e8832ba2b012f9ae2 | Apache-2.0 | OPUS declared; no NC dataset declared in reviewed model metadata; source-license inventory remains incomplete | COMMERCIAL_DEFAULT under the uniform rule; legal-risk note retained | 2026-10-03 |
| B NLI | cross-encoder/nli-deberta-v3-base | dcaec5ddc7a9456405d53c33bb2d4050ca4f75cf | Apache-2.0 | SNLI (CC BY-SA 4.0); MultiNLI (majority OANC/permissive, with share-alike/permissive components declared); no NC term identified in reviewed metadata | COMMERCIAL_DEFAULT under the uniform rule | 2026-10-03 |
| Candidate | google/madlad400-3b-mt | fa184c675da0b5c9e1c8694fccd4e12e2d422094 | Apache-2.0 | MADLAD-400; model card says publicly available data; no NC dataset declared | COMMERCIAL_DEFAULT under the uniform rule | 2026-10-03 |
| Candidate | ibm-granite/granite-guardian-3.3-8b | fixed revision required before activation | Apache-2.0 | IBM/HF model card: English; training-data details are not a dataset-by-dataset NC declaration; no NC dataset declared | COMMERCIAL_DEFAULT under the uniform rule; external comparator only | 2026-10-03 |
| Candidate | ibm-granite/granite-guardian-4.1-8b | ab01ccca5dcfb80246369a086a4a87a29198f5af | Apache-2.0 | IBM/HF: English; human + synthetic/internal red-team data; no NC dataset declared | COMMERCIAL_DEFAULT under the uniform rule; external comparator only | 2026-10-03 |
| MiniCheck | lytang/MiniCheck-Flan-T5-Large | fixed revision required before activation | MIT | 21K ANLI + 14K synthetic training recipe; ANLI is CC BY-NC 4.0 | EVAL_ONLY | 2026-10-03 |
| MiniCheck | lytang/MiniCheck-DeBERTa-v3-Large | fixed revision required before activation | MIT | 21K ANLI + 14K synthetic training recipe; ANLI is CC BY-NC 4.0 | EVAL_ONLY | 2026-10-03 |
| MiniCheck | lytang/MiniCheck-RoBERTa-Large | fixed revision required before activation | MIT | released MiniCheck-RBTA uses the 14K synthetic set; no ANLI declared for this variant; training-data licensing is not fully inventoried | COMMERCIAL_DEFAULT only under the uniform declared-data rule, pending exact revision and provenance inventory | 2026-10-03 |
| Bespoke MiniCheck | bespokelabs/Bespoke-MiniCheck-7B | 1ed7786bcda3fa1dc35f7c4ed9e3f36b785d33b8 | CC BY-NC 4.0 | 21K ANLI + 14K synthetic | EVAL_ONLY | 2026-10-03 |

### Important MiniCheck nuance

The MiniCheck paper states that **MiniCheck-DBTA and MiniCheck-FT5** use 21K selected ANLI training examples plus 14K synthetic examples. **MiniCheck-RBTA** is described as trained on the 14K synthetic dataset only. Therefore the three variants must not be collapsed into one identical training-data claim.

## Runtime enforcement

The optional NLI backend has a license guard. EVAL_ONLY backends are rejected unless evaluation mode or an explicit opt-in is active. Provenance records the gate state.

## Legal notice

This policy is not legal advice. Model and dataset licensing can involve additional rights, contracts and jurisdiction-specific issues; review by qualified intellectual-property counsel is recommended before commercial use.
