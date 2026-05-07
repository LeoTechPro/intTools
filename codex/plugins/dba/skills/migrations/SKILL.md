---
name: migrations
description: dba migrations. Используйте только для gated migration workflows, readiness checks и owner-approved apply.
---

# intDBA migrations

## When to use
- Use for migration readiness, migration status, and owner-approved migration apply workflows.

## Do first
- Confirm the target profile and whether the request is status-only or apply.
- Prefer `intdata_cli` or the plugin migration surface.
- Summarize migration status, pending items, and apply result or blocker.

## Expected result
- The intended migration workflow is completed with clear approval boundaries.

## Checks
- Status-only requests remain read-only.
- Apply requests include explicit approval and `issue_context=INT-*`.
- The target profile is explicit.

## Stop when
- The profile is unknown.
- Mutation is requested without approval.
- The tool returns policy or config errors.

## Ask user when
- More than one migration target could match.
- Apply semantics or target contour are unclear.

## Tool map
- `intdata_cli`: use `command="dba"` for `migrate status` or approved `migrate apply` paths with an explicit profile.
