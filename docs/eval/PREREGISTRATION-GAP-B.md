# Pre-registration: GAP B excerpt revalidation
Date: 2026-10-04. Frozen; changes only as dated amendments.
H-B1: Locating each excerpt in the original source, instead of trusting supplied offsets, changes no verdict on Golden v0 or v0.1.
H-B2: Evidence whose excerpt is not found verbatim in its source is excluded, so a claim backed only by forged excerpts cannot be VERIFIED or SUPPORTED.
Design: locate_excerpt(source_text, excerpt) returns (start, end) or None; exact match after Unicode NFC only; no fuzzy matching; first occurrence. Supplied offsets are ignored. Not found: evidence dropped, audit reason "excerpt_not_in_source".
Disclosed data issue: of 52 corpus documents, 37 have no offsets, 2 match the content, 13 differ; doc-034, doc-035, doc-036 and doc-044 end beyond the content. The frozen corpus will not be edited.
Measurement: per-claim verdicts before/after on Golden v0 and v0.1 (path C locally; golden-regression and judge-regression in CI). Prediction: 0 changes. Adversarial tests must all pass.
Decision: if any verdict changes, do not merge; report as negative result.
Out of scope: fuzzy matching, translated alignment, Golden v1.
