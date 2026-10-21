# Proposed dated amendment — RGC invalid-prediction handling (20/10/2026)

**Current status (2026-10-21):** Option A approved explicitly by the maintainer in Prompt Master 2 on 2026-10-21.  
**Immediate effect:** none. This proposal does not alter the active pre-registration, freeze the protocol, authorize definitive annotation, or authorize a confirmatory execution.

**Corrective note (2026-10-21):** PR #323 marked Option A as approved. The current Master Prompt requires DEC-017 to remain pending until the maintainer explicitly decides the scientific question. The previous status is preserved in Git history and summarized in the historical note below; it is not the current normative state.

**Nota (2026-10-21):** superada pela Emenda 7 aprovada (DEC-017); mantida apenas como histórico.

## Reason

The proposed pre-registration `docs/eval/PREREGISTRATION-RGC-v1.md`, §4, says that missing or invalid predictions will be reported as execution failure. The current RGC runner and `docs/eval/STATISTICS.md` distinguish two situations:

- a missing prediction record or structurally inconsistent prediction file is an input-integrity failure and aborts the run;
- a present per-case prediction that cannot be mapped to the five-state `judge2` vocabulary is recorded as `INVALID_PREDICTION`, remains in the denominator, and counts as an incorrect prediction.

The current text should not be silently reinterpreted. This proposal records a precise wording change for explicit review.

## Proposed replacement wording for the final paragraph of §4

> A prediction file must contain exactly one prediction for each evaluable case. Missing or duplicate records, unknown case IDs, missing human labels, or other input-integrity violations invalidate the run and must stop execution; such cases must not be silently removed or imputed. A present per-case system output that cannot be mapped to the RGC `judge2` vocabulary is recorded as `INVALID_PREDICTION`, remains in the evaluation denominator, and counts as an incorrect prediction. The report must publish the count of invalid predictions. This distinction is part of the pre-specified evaluation contract and must not be changed after observing confirmatory results without a dated amendment approved before a new run.

## Safeguards

- This proposal does not alter the active pre-registration.
- It does not alter Judge behavior, labels, Golden fixtures, or historical results.
- It does not authorize the pilot or definitive annotation, nor a confirmatory run.
- The pilot 02 remains human-only: no AI to draft or label cases, and no ATTRACTOR execution on pilot cases.
- If approved, the replacement must be applied through a dated, auditable amendment preserving the previous wording and decision history.

## Maintainer decision

- [ ] Approved explicitly by Anderson Leon Ayora — Option A
- [ ] Rejected
- [ ] Changes requested

**Decision date:** pending.  
**Decision owner:** Anderson Leon Ayora.

## Historical status note (2026-10-21)

PR #323 recorded the following prior state: “Status: approved by maintainer on 2026-10-21; Option A,” checked “Approved explicitly by Anderson Leon Ayora — Option A,” and assigned decision date 2026-10-21. This historical entry is retained for traceability. Under the current Master Prompt, DEC-017 remains pending and the recorded approval is not treated as a current decision.

**Nota (2026-10-21):** superada pela Emenda 7 aprovada (DEC-017); mantida apenas como histórico.


**Approval record (2026-10-21):** Option A is the operative decision. Missing/duplicate prediction records, unknown case IDs, missing human labels, or malformed input stop the run; a present output unmappable to `judge2` becomes `INVALID_PREDICTION`, stays in the denominator, and counts as an error. The protocol remains proposed and unfrozen; no confirmatory run is authorized by this approval.

**Nota de consistência (2026-10-21):** a aprovação normativa é a decisão do mantenedor registrada na DEC-017 e formalizada pela Emenda 7; as passagens anteriores que dizem que DEC-017 está pendente são apenas histórico.
