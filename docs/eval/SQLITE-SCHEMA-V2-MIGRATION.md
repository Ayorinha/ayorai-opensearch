# SQLite audit schema v2 and baseline provenance

## Audit schema migration

The audit store uses SQLite `PRAGMA user_version` as its schema-version marker. Schema v2 is
created for new databases and is migrated idempotently from the prior `audit_traces` schema.

- `legacy_verification` retains the exact previous verification text for historical records.
- `verification` is nullable and remains `NULL` for new records; it is not a factual verdict.
- `operation_status` records operational completion/failure separately from factual adjudication.
- `replay_version` identifies the replay digest contract (`r2-v1` or `r2-v2`).
- `schema_version` records the row's schema generation; new and migrated rows use `2`.
- `replay_digest` is copied without recalculation during migration. Historical rows that match the
  known `r2-v2` canonical event are identified as `r2-v2`; other historical digests are retained
  as `r2-v1` without repair or silent replacement.

The migration does not delete, rewrite, or regenerate the frozen evaluation artifacts. It uses
temporary SQLite databases in tests and checks both repeat-migration idempotence and digest
preservation, including a corrupted-digest fixture.

## Historical legacy baseline provenance

The legacy baseline was measured in workflow run
[36759101933](https://github.com/Ayorinha/ayorai-opensearch/actions/runs/36759101933).
The maintainers verified 68/68 predictions against commit
`3be512b8ae60e6a1b98524b005c8bf1e1d22aaf4`.

The `baseline-legacy-v0` reference is a **lightweight Git tag with a GitHub pre-release for
provenance**, created through the GitHub web interface. Provenance is recorded in the release
description; it is not stored in an annotated-tag object. The tag points to the historical source
commit, not to the current product release. Do not regenerate the frozen baseline from current
`main`; use a checkout of the historical tag when reproducing the legacy measurement.
