# Release provenance plan

This document records the release-hardening requirements for F6. It does not claim that the release controls are already implemented.

## Required release evidence

1. **SLSA provenance**
   - Use the reusable workflow from `slsa-framework/slsa-github-generator`.
   - Use `generator_generic_slsa3.yml` at the job level.
   - Publish the SHA-256 hashes of release artifacts as the SLSA subjects.

2. **OpenTimestamps**
   - Generate an `.ots` file for the SHA-256 digest of the release artifact set.
   - Attach the timestamp proof to the GitHub release.

3. **SBOM**
   - Generate and attach an SBOM for each release artifact set.

4. **Release signatures**
   - Sign the release artifacts and publish verification metadata.

5. **Replayability**
   - Record the release commit, artifact hashes, SBOM, provenance and timestamp proof together so a release can be independently replayed and checked.

## Current status

These are F6 release requirements. No F6 release-provenance implementation is claimed by this document.
