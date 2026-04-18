---
name: intdata-control-openspec-read
description: Use for read-only OpenSpec discovery, show, status, instructions, and validation through intData Control MCP tools.
---

# intData Control: OpenSpec Read

Use this when a task mentions plans, specs, proposals, active changes, acceptance, or source-of-truth checks.

## Tools

- `openspec_list`
- `openspec_show`
- `openspec_status`
- `openspec_validate`
- `openspec_instructions`

## Rules

- Read `openspec/AGENTS.md` before planning or implementing tracked tooling changes.
- Treat OpenSpec as source-of-truth for requirements and acceptance.
- Use `cwd="D:/int/tools"` unless the task is explicitly scoped elsewhere.
- Read-only OpenSpec tools do not require mutation confirmation.

## Blockers

- No relevant active change for a tracked tooling mutation.
- Spec contradicts requested implementation.
- OpenSpec MCP unavailable and owner has not approved direct wrapper fallback.

## Fallback

Direct `openspec` wrappers are fallback only after recording the MCP blocker.

## Examples

- List changes: `openspec_list(cwd="D:/int/tools")`
- Show change: `openspec_show(cwd="D:/int/tools", item="agent-tool-plane-v1")`
- Validate: `openspec_validate(cwd="D:/int/tools", item="agent-tool-plane-v1", strict=true)`
