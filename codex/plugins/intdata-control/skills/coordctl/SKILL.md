---
name: coordctl
description: Coordctl Git-aware coordination для параллельных agent edits. Используйте для session/intent leases, hunk-level coordination, heartbeat, release, status и merge dry-run как primary coordination runtime.
---

# coordctl

## When to use
- Use for Git-aware coordination before tracked edits, when checking active leases, or when releasing coordination state.

## Do first
- Prefer `mcp__intdata_control__coordctl_*` tools.
- Verify `repo_root`, branch or base, and current issue context before any mutating call.
- Treat shell fallback as degraded mode only; do not replace `COORD_CONFLICT`, `STALE_BASE`, or policy errors with ad hoc commands.
- Summarize returned session ids, lease ids, conflicts, and cleanup status in worklog or final output.

## Expected result
- One clear coordination action is taken: start, acquire, inspect, renew, release, cleanup, GC dry-run, or merge check.

## Checks
- Mutating calls have explicit approval and, when applicable, `issue_context=INT-*` plus `confirm_mutation=true`.
- Lease scope is specific to a file or hunk, not a broad directory.
- `coordctl_status` or `coordctl_merge_dry_run` is used when the task is inspection-only.

## Stop when
- Required args are missing.
- MCP returns `COORD_CONFLICT`, `STALE_BASE`, policy, or config errors.
- Repo root, branch, base, or lease scope is unclear.
- The request would mutate coordination state without approval.

## Ask user when
- The correct repo, branch, or issue is not confirmed.
- A lease conflict needs a coordination decision rather than a retry.
- Cleanup would delete worktree or branch state.

## Tool map
- `coordctl_session_start`: mutating; inputs `repo_root`, `owner`, `branch`, `base`; optional `issue`, `worktree_path`, `lease_sec`.
- `coordctl_intent_acquire`: mutating; inputs `repo_root`, `path`, `owner`, `base`, `region_kind`, `region_id`; optional `issue`, `lease_sec`, `session_id`.
- `coordctl_status`: read-only; input `repo_root`; optional `path`, `owner`, `issue`, `all`.
- `coordctl_heartbeat`: mutating; input `session_id`; optional `lease_sec`.
- `coordctl_release`: mutating; optional `session_id`, `repo_root`, `issue`.
- `coordctl_cleanup`: mutating; input `session_id`; optional `final_state`, `delete_worktree`, `delete_branch`, `dry_run`, `apply`.
- `coordctl_gc`: mutating maintenance; optional `dry_run`, `apply`.
- `coordctl_merge_dry_run`: read-only; inputs `repo_root`, `target`, `branch`.
