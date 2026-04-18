---
name: intdata-control-lockctl
description: Use for `/int/tools` file lock workflows with intData Control: acquire, renew, release, status, and expired-lock cleanup.
---

# intData Control: lockctl

Use this before any tracked file mutation in `/int/tools` and when inspecting lock conflicts.

## Tools

- `lockctl_status`: read active or expired locks.
- `lockctl_acquire`: acquire or renew a file lock.
- `lockctl_renew`: renew by `lock_id`.
- `lockctl_release_path`: release one path lock.
- `lockctl_release_issue`: release all locks for an `INT-*` issue.
- `lockctl_gc`: delete expired locks.

## Rules

- Required inputs for path operations: `repo_root`, `path`, `owner`.
- Use full `INT-*` in `issue` for issue-bound work.
- Do not edit a tracked file if another active owner holds its lock.
- Release locks after finishing or when handing off.

## Blockers

- Unknown repo root or target path.
- Active lock owned by someone else.
- Missing Multica issue for non-trivial `/int/tools` implementation.

## Fallback

Use direct lockctl CLI only after recording the MCP blocker and owner approval.

## Examples

- Status: `lockctl_status(repo_root="D:/int/tools", path="codex/plugins/intbrain/skills/SKILL.md")`
- Acquire: `lockctl_acquire(repo_root="D:/int/tools", path="...", owner="codex", issue="INT-226")`
- Release issue: `lockctl_release_issue(repo_root="D:/int/tools", issue="INT-226")`
