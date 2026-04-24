# INT-337

## Summary

Consolidate the tracked `/int/tools` operator layer around the canonical role matrix already approved for live cleanup:

- `agents` replaces `db_admin_prod` and `db_admin_dev` in tracked admin wrapper paths
- `db_readonly_prod` becomes the tracked readonly role for both `punkt_b_prod` and `punkt_b_legacy_prod`
- tracked runbooks stop advertising `db_readonly_legacy`

The change is limited to operator-facing tooling and runbooks in `/int/tools`. Historical SQL plans remain untouched.

## Why

Live host cleanup and role consolidation require the tracked operator surface to match the canonical runtime:

- admin wrappers must point to `agents`
- legacy readonly wrappers must point to `db_readonly_prod`
- current docs must stop instructing operators to use removed roles

## Acceptance

- `intdb` admin entrypoints reference `agents`
- `intdb` legacy readonly entrypoint references `db_readonly_prod`
- current `intdb` docs and active Punkt-B runbooks no longer instruct operators to use `db_admin_prod`, `db_admin_dev`, or `db_readonly_legacy`
