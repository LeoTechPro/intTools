---
name: intdata-control-multica
description: Use for Multica issue, project, repo, agent, runtime, workspace, skill, attachment, auth, config, and daemon coordination.
---

# intData Control: Multica

Use this for task control-plane operations. GitHub Issues are not fallback coordination for `/int/tools`.

## Tools

- `multica_issue`, `multica_project`, `multica_repo`, `multica_agent`
- `multica_workspace`, `multica_skill`, `multica_runtime`
- `multica_attachment`, `multica_auth`, `multica_config`
- `multica_daemon`, `multica_exec`

## Rules

- Use full issue identifiers such as `INT-226`, not short UUIDs.
- Read-only commands include list/get/search/ping/status-like operations.
- Mutating commands require `confirm_mutation=true` and `issue_context="INT-*"`.
- Worklog/status/blockers/closure belong in Multica, not OpenSpec.

## Blockers

- Issue cannot be verified.
- Tool returns auth or daemon errors.
- Owner has not approved mutating issue or daemon operations.

## Fallback

Direct `multica` CLI is fallback only after MCP blocker and owner approval.

## Examples

- Search: `multica_issue(command="search", args=["Agent Tool Plane"])`
- Get: `multica_issue(command="get", args=["INT-226"])`
- Mutate: `multica_issue(command="comment", args=["INT-226", "..."], confirm_mutation=true, issue_context="INT-226")`
