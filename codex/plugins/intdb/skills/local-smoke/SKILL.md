---
name: intdb-local-smoke
description: Use for owner-gated disposable local Supabase/intdb smoke workflows.
---

# intdb: Local Smoke

Use this for disposable local Supabase smoke checks, not production DB work.

## Tools

- `intdata_cli`

## Rules

- Confirm the workflow uses a disposable local target.
- Mutating local-test/bootstrap/apply steps require `confirm_mutation=true` and `issue_context="INT-*"`.
- Keep runtime state and secrets outside tracked git.

## Blockers

- Target is not disposable/local.
- Docker/Supabase runtime prerequisites are unavailable.
- Task would change production state.

## Fallback

Direct local scripts require MCP blocker and owner approval.

## Examples

- Help: `intdata_cli(command="intdb", args=["local", "--help"])`
- Local smoke: `intdata_cli(command="intdb", args=["local", "smoke"], confirm_mutation=true, issue_context="INT-226")`
