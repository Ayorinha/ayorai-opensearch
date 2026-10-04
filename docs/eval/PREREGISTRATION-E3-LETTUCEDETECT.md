# PREREGISTRATION — E3 LettuceDetect Evaluation

Status: frozen before E3 measurement
Date: 2026-10-04
Base commit: 86d1bdaf4464147416adcff7ac56259061629f7d

## Hypothesis and scope

E3 evaluates LettuceDetect as Path D, an evidence-span detector for unsupported claims.
It is **EVAL_ONLY**. It does not replace the deterministic Judge, FACT/NLI stance,
or final verdict. No training or fine-tuning is performed in E3.

Because Portuguese coverage is not established for LettuceDetect, evaluate:
1. PT direct: original Portuguese documents passed directly to the detector.
2. PT via translation: the full Portuguese document translated to English first,
   then evaluated by LettuceDetect.

The translation path is an evaluation-only comparison; translation is not a verdict rule.

## Frozen rules

- Do not change ADR-002 verdict precedence or thresholds.
- Do not tune thresholds against Golden v0 or v0.1.
- Do not rerun H1.
- Keep Golden v0 and v0.1 as development sets only.
- Generalization claims require hidden Golden v1.
- Record the exact LettuceDetect model/revision, weights/data license status,
  runtime, and translation model/revision.
- If weights or data licensing is not independently cleared for the intended use,
  retain the path as EVAL_ONLY.
- No LLM Judge is introduced.

## Evaluation

Use the same claim/evidence cases and fixed IDs from the current evaluation suites where
the detector's input assumptions permit measurement. Report coverage and supported-span
detection separately from final verdict accuracy; E3 is not a replacement for the
deterministic verdict pipeline.

Metrics:
- detector precision, recall, F1 where gold span labels exist;
- unsupported-span detection precision/recall/F1 where applicable;
- coverage/abstention;
- latency p50/p95;
- bootstrap 95% CI with 10,000 resamples, seed 20261003;
- per-category results;
- exact paired comparisons where a paired detector decision is defined.

For PT direct versus PT-translation, report paired results on the same eligible cases.
Do not infer general Portuguese performance beyond the measured Golden cases.

## Reproducibility

Report:
- commit SHA;
- Golden SHA-256;
- LettuceDetect model/revision;
- translation model/revision;
- licenses and source/date for external model/data claims;
- report SHA-256;
- GitHub Actions run/job/artifact links.

## Stopping rule

E3 ends after the two authorized evaluation paths (PT direct and PT via translation)
have been measured and reported, plus reproducibility metadata. No model training,
threshold optimization, or architecture promotion occurs in E3.

## Disclosure

E3 is authorized after the audited E2 result. The negative H1 result is known before
this preregistration and is not a criterion for selecting or tuning LettuceDetect.

## Amendment — 2026-10-03

This amendment preserves the original E3 preregistration above and corrects its
evaluation scenario to match the actual Golden corpus.

### Actual corpus scenario

The current Golden corpus contains English (en-US) documents and Portuguese claims
(34 PT claims and 3 EN claims in Golden v0.1). There are no Portuguese documents in
the current Golden corpus. Therefore the originally preregistered PT-document arms
cannot be measured on the current corpus.

### Authorized E3 arms

- **D1 — PT claim / EN document:** use the original Portuguese claim as the
  LettuceDetect "answer" and the English document as "context".
- **D2 — translated claim / EN document:** translate the same Portuguese claim
  from PT→EN using the same Opus-MT translation path/revision already used in the
  evaluated B path, then use the translated claim as "answer" and the same English
  document as "context".
- **MADLAD-400 is removed from E3.** It is not used because the current Golden has
  no Portuguese documents. MADLAD-400 remains reserved for a future evaluation when
  the Golden contains Portuguese documents.

### Fixed decision rule

Use the LettuceDetect library default threshold without any adjustment or tuning.
If LettuceDetect marks any portion of the claim as unsupported, classify D as
**NAO_SUSTENTADO**. Otherwise classify D as **SUSTENTADO**.

### Binary gold

Map the expected stance to the binary target:
- SUPPORTS → **SUSTENTADO**
- CONTRADICTS or NEUTRAL → **NAO_SUSTENTADO**

Span precision/recall/F1 are **not applicable**, because the current Golden corpus
does not contain gold span labels.

### Primary metric and paired comparisons

The primary metric for D1 and D2 is **binary balanced accuracy**.
Report McNemar D1 vs D2.

Also reduce A, B, and C to the same binary rule and report exact paired McNemar
comparisons of D against A, B, and C on the same eligible cases.

### Project limitation

The current Golden does not contain documents in Portuguese. Golden v1 must include
Portuguese documents so that true PT-document evaluation, including a PT-direct arm,
can be measured.