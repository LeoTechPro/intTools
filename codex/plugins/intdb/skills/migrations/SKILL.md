---
name: intdb-migrations
description: Use for intdb migration status, planning, and owner-gated migration apply workflows.
---

# intdb: Migrations

Use this for migration status and approved migration application.

## Tools

- `intdata_cli`

## Rules

- Status/read-only migration commands may run without mutation confirmation.
- Migration apply is mutating/high-risk: require `confirm_mutation=true`, `issue_context="INT-*"`, and explicit owner approval.
- For `/int/data`, migration changes must match approved OpenSpec/source-of-truth.

## Blockers

- Missing profile/secret.
- Target is production and owner did not explicitly approve.
- Spec/source-of-truth is absent or contradictory.

## Fallback

Direct intdb CLI requires MCP blocker and owner approval.

## Examples

- Status: `intdata_cli(command="intdb", args=["migrate", "status"])`
- Apply: `intdata_cli(command="intdb", args=["migrate", "apply"], confirm_mutation=true, issue_context="INT-226")`
