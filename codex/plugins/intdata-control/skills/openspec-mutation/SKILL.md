---
name: intdata-control-openspec-mutation
description: Use for owner-approved OpenSpec lifecycle mutations: new changes, change/spec edits, archive, and mutating OpenSpec commands.
---

# intData Control: OpenSpec Mutation

Use this only when the owner approved lifecycle mutation or an existing active change must be updated for the current scope.

## Tools

- `openspec_new`
- `openspec_change`
- `openspec_spec`
- `openspec_archive`
- `openspec_exec`

## Rules

- Mutating calls require `confirm_mutation=true` and `issue_context="INT-*"`.
- Create or update `proposal.md`, `tasks.md`, and spec deltas before code changes.
- Prefer updating an existing relevant change over creating a parallel change.
- Validate the change after edits.

## Blockers

- Missing owner approval for spec lifecycle mutation.
- Missing or unverifiable `INT-*`.
- Ambiguous source-of-truth.

## Fallback

No direct CLI fallback without explicit owner approval after MCP failure.

## Examples

- New change: `openspec_new(cwd="D:/int/tools", issue_context="INT-226", confirm_mutation=true, args=["agent-tool-plane-v1"])`
- Archive: `openspec_archive(cwd="D:/int/tools", issue_context="INT-226", confirm_mutation=true, change_name="agent-tool-plane-v1")`
- Guard check: call without `confirm_mutation` should fail.
