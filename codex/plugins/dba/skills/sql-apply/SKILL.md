---
name: sql-apply
description: dba SQL/apply. Используйте для controlled SQL execution/apply workflows с read-only dry-run мышлением и явным approval gate.
---

# intDBA SQL apply

## When to use
- Use for controlled SQL execution or apply workflows that are already approved.

## Do first
- Confirm the target profile, SQL source, and blast radius.
- Prefer the plugin or `intdata_cli` surface instead of ad hoc shell SQL.
- Summarize the target profile, SQL scope, and apply result or blocker.

## Expected result
- The intended SQL apply workflow is executed against the correct approved target.

## Checks
- The target profile is explicit.
- Mutation includes approval and `issue_context=INT-*`.
- Read-only inspection has already answered what can be answered without apply.

## Stop when
- The profile or SQL target is unknown.
- Mutation is requested without approval.
- The tool returns policy or config errors.

## Ask user when
- More than one SQL target or profile could match.
- The SQL source or expected side effects are unclear.

## Tool map
- `intdata_cli`: use `command="dba"` with approved SQL apply or execution args on the intended profile.
