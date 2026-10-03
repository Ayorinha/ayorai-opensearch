# P0C — F0 Stabilization Results

## Recovery trigger

External review of p0-pipeline at c3b0deb found that the F0 report no longer matched the code: the verification path had regressed to retriever-derived claims, evaluation/golden.py called a mismatched ClaimVerificationPipeline constructor, and the regression suite was not green.

The pre-F0 abstention contract was 4/4, not 0/4.

## Recovery

Recovery branch: fix/f0-recovery.

claim_pipeline.py, extraction.py and stance.py were restored from 9e119a5 and then changed incrementally. The recovery also restored claim-as-input regression tests, added strict LLM payload validation, normalized processing errors to ABSTAIN/PROCESSING_ERROR, added the retriever guard, and closed Ruff/mypy/security regressions.

The verification contract is explicit: ClaimVerificationPipeline.verify(claims, documents) receives caller-supplied claims; verify() has no retriever parameter; claim extraction receives only the model response; the deterministic Judge remains the verdict authority.

## Post-F0 Golden v0

CI run: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/37133387080
HEAD: 7478f7a320285e033a683620b60ad0a60153efe8
Artifact: golden-v0-38d183c53a5990aec1b1b0977051e35fdcf5c95f
Report digest: a7e83161b613c6af81645e1a4daf8fc55331615a55242b509616855d68fe737a

| Metric | Post-F0 |
|---|---:|
| Cases | 34 |
| Corpus documents | 52 |
| Global verdict cases | 30 |
| Accuracy | 8/30 = 26.6667% |
| Majority baseline | 13/30 = 43.3333% |
| Balanced accuracy | 44.0171% |
| Bootstrap 95% CI | [13.3333%, 43.3333%] |
| McNemar vs legacy | 9 legacy-correct/new-wrong; 4 new-correct/legacy-wrong; exact p=0.266845703125 |
| Abstention contracts | 4/4 |
| ABSTAIN/NO_ANSWER | 2/2 |
| ABSTAIN/OUT_OF_SCOPE | 2/2 |
| Report SHA-256 | a7e83161b613c6af81645e1a4daf8fc55331615a55242b509616855d68fe737a |

Post-F0 accuracy is unchanged from the measured pre-recovery diagnostic (8/30). F0 is stabilization/recovery, not an accuracy-improvement claim.

## CI evidence

At HEAD 7478f7a, test 3.11, test 3.12, test 3.13, namespace compatibility, Golden lint, Golden smoke, Golden regression, Judge regression, strict typecheck, security, CodeQL and analyze completed successfully.

Dependency Review remains the only failing check because GitHub reports that Dependency Graph is disabled for the repository. This is a repository setting, not a code/test failure.

## Exit status

F0 code/test/type/security/CodeQL gates are green at 7478f7a. F0 is not marked fully closed until Dependency Graph is enabled and Dependency Review passes. PR #85 is not merged here.
