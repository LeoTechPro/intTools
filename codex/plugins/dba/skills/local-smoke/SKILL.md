---
name: local-smoke
description: dba local smoke. Используйте для read-only SQL smoke и локальных проверок профилей без apply.
---

# intDBA local smoke

## When to use
- Use for read-only SQL smoke checks on approved local or read-only profiles.

## Do first
- Confirm the profile and exact smoke target.
- Prefer `intdata_cli` read-only execution.
- Summarize the smoke query or command and the verdict.

## Expected result
- A read-only smoke result for the intended DBA profile.

## Checks
- The command stays read-only.
- The selected profile is explicit and safe for smoke checks.

## Stop when
- The profile is unknown.
- The request drifts into apply or mutation.
- The tool returns policy or config errors.

## Ask user when
- More than one local profile could match.
- The smoke query could mutate state.

## Tool map
- `intdata_cli`: use `command="dba"` with read-only smoke-oriented args on the intended profile.
