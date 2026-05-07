---
name: doctor-status
description: intDBA doctor/status. Используйте для read-only проверки профилей, состояния подключения и безопасной диагностики intDBA.
---

# intDBA doctor and status

## When to use
- Use for read-only profile, connectivity, and health diagnostics.

## Do first
- Confirm the target profile.
- Prefer `intdata_cli` with read-only DBA subcommands.
- Summarize profile, command, and diagnostic verdict.

## Expected result
- A read-only diagnostic answer for the intended DBA profile.

## Checks
- `doctor`, `status`, or `migrate status` is enough for the request.
- The selected profile is explicit and safe for diagnostics.

## Stop when
- The profile is unknown.
- The request would trigger apply, dump, restore, or other mutation.
- The tool returns policy or config errors.

## Ask user when
- More than one profile could match.
- The user is really asking for mutation rather than diagnostics.

## Tool map
- `intdata_cli`: use `command="dba"` with read-only subcommands such as `doctor`, `status`, or `migrate status`; profile is usually required.
