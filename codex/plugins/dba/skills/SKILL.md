---
name: dba
description: Internal int-tools skill entrypoint for the dba plugin. Use as the router for dba doctor/status, read-only SQL smoke, migrations, and controlled SQL apply workflows.
---

# intDBA

## When to use
- Use for intDBA doctor and status checks, read-only SQL smoke, migration readiness, and controlled SQL apply workflows.

## Do first
- Prefer the `dba` MCP or `intdata_cli` surface instead of ad hoc shell commands.
- Pick the narrowest leaf skill for the requested workflow.
- Confirm the target profile and whether the task is read-only or mutating.
- Summarize material command results, profile used, and apply status in worklog or final output.

## Expected result
- The correct DBA workflow is chosen with a clear profile and mutation mode.

## Checks
- Profile and target environment are explicit.
- Read-only requests stay read-only.
- Mutating requests carry explicit approval and issue context.

## Stop when
- Required args are unknown.
- MCP returns policy or config errors.
- The task needs mutation without approval.
- Profile or environment scope is ambiguous.

## Ask user when
- More than one profile or target environment could match.
- Apply, dump, restore, clone, or local-test semantics are unclear.

## Skill map
- `doctor-status`: read-only health and connection diagnostics.
- `local-smoke`: read-only SQL smoke checks.
- `migrations`: migration readiness, status, and approved apply workflow.
- `sql-apply`: controlled SQL execution with explicit approval.
