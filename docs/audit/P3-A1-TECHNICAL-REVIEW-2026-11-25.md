# P3/A1 technical review — 2026-11-25

## Scope and reference

- Repository: `Ayorinha/ayorai-opensearch`
- Reference `main`: `3932d171fa5b4554684ec247555d3eaa8081e568`
- PR #635 HEAD: `119a219f8be420af2ab12b427b05cac8f7ab4e56`
- PR #636 HEAD: `b8854d389f640670cc2bf7a0f9b7357f723f6110`
- This is a targeted static review of the P3/A1 DEV gold-label isolation and inference-artifact integrity changes. It is not an independent human review, a security certification, or a validation of benchmark results.

## Verified repository and PR state

### Main

The current main reference consulted for this review is `3932d171fa5b4554684ec247555d3eaa8081e568`. The repository's `AGENTS.md` assigns the maintainer sole authority over merges, releases, and governance decisions; requires independent review where applicable; protects Judge, Golden, manifests, hashes, and RGC normative artifacts; and prohibits agents from creating or viewing benchmark cases or running the system on pilot/hidden data.

### PR #635 — isolate DEV gold labels from inference

- URL: https://github.com/Ayorinha/ayorai-opensearch/pull/635
- State: open, Draft; base `main`.
- HEAD: `119a219f8be420af2ab12b427b05cac8f7ab4e56`.
- Changed files: 28.
- GitHub Actions workflow runs returned for this exact HEAD: 8, all completed with conclusion `success`: CI, Security, CodeQL, Dependency Review, Schemathesis Full API Contract, API Contract Guard, Artifact Download Action Smoke, Golden r2 Migration.
- No independent human review is recorded in the review list.

Static inspection of the relevant files confirms:
- The preparation step writes an inference-only JSONL with `record_id`, document, claim and cohort, and separately builds an AES-256-GCM gold-label envelope.
- Gold labels and prediction/score cache use distinct keys; the preparation and aggregation paths reject equal keys.
- The persisted score cache rejects gold fields; the persisted gold-label cache is a separate encrypted envelope.
- The full, minimal, reaggregate and cache-experiment workflows include explicit `github.ref == 'refs/heads/main'` guards on their privileged jobs.
- The full workflow uploads encrypted manifest and inference input artifacts; the manifest's per-record IDs are not uploaded as plaintext.
- The aggregate joins labels and predictions only inside the evaluation process; output validation rejects instance-level fields from the published aggregate.

These are source-level observations plus the listed CI results. They do not prove the GitHub Environment's branch restrictions, secret provisioning, or behavior in a protected operational execution.

### PR #636 — verify inference artifact digest

- URL: https://github.com/Ayorinha/ayorai-opensearch/pull/636
- State: open, Draft; base is intentionally the #635 branch.
- HEAD: `b8854d389f640670cc2bf7a0f9b7357f723f6110`.
- Changed files: 2.
- No GitHub Actions workflow runs and no commit status contexts were returned for this exact HEAD during this review. Therefore its CI is **unverified**, not passed.

Static inspection confirms that the PR:
- Requires `inference_dataset_sha256` to be a 64-character lowercase hexadecimal digest in the DEV manifest.
- Verifies the input bytes against that digest before encryption.
- Verifies decrypted bytes against the same digest before writing plaintext output.
- Adds synthetic tests for missing/invalid digest, pre-encryption mismatch, post-decryption mismatch, wrong key, changed provenance, and successful round-trip.
- Ensures the output file is not written when the post-decryption digest check fails.

The digest is obtained from the encrypted/authenticated manifest flow. The code change is narrow and preserves the existing AES-GCM metadata checks. Static inspection is not a substitute for CI or independent review.

## Remaining blockers

1. **CI for #636:** obtain the full required workflow set on the exact HEAD `b8854d389f640670cc2bf7a0f9b7357f723f6110`. Do not infer its success from #635.
2. **Independent review:** #635 and #636 need a reviewer other than the author/maintainer's automated self-review where the repository governance requires it. This review does not satisfy that requirement.
3. **Retention decision:** the full/reaggregate workflows currently set 90 days for both the gold-label cache and score cache. The prior seven-day decision for encrypted manifests/shards does not automatically determine retention for these new cache artifacts. The maintainer must decide the policy; no retention value was changed here.
4. **Protected environment and secrets:** the maintainer must verify the protected Environment's allowed branches/approvals and provision the required secrets manually. No secrets were inspected, changed, or tested.
5. **Operational authorization:** do not dispatch full/minimal/reaggregate/cache experiment workflows until the preceding gates are satisfied and the maintainer explicitly authorizes the specific operation.

## Findings and recommendations

- No confirmed source-level defect was found in the two inspected inference-artifact digest checks.
- The main outstanding technical evidence gap is the absence of CI results for #636.
- Keep both PRs Draft. Do not approve or merge them as part of this review.
- Keep retention policy pending until the maintainer makes the decision.
- After CI and independent review, re-check the exact final HEADs and all changed files before considering the A1 task complete.

## Actions not performed

- No merge, approval, release, tag, or branch-protection bypass.
- No Judge, Golden, RGC, manifest, hash, threshold, or protected source change.
- No benchmark case was created, viewed, reviewed, or labeled.
- No DEV or TEST inference, benchmark execution, or workflow dispatch occurred.
- No secret was accessed or modified.
- No claim of external validation, benchmark validity, or production readiness is made.

## Conclusion

P3/A1 is **not complete**. The implementation is substantially present and #635 has passing CI on its exact HEAD, but #636 still lacks recorded CI evidence, independent review remains outstanding, and the cache-retention policy is a maintainer decision. The next safe step is to obtain CI evidence for #636 and independent review while leaving protected execution disabled.
