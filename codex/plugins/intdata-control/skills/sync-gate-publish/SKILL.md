---
name: intdata-control-sync-gate-publish
description: Use for `/int/tools` sync-gate, publication, push, deploy, and owner-approved finish workflows.
---

# intData Control: Sync Gate and Publish

Use this before starting or finishing tracked `/int/tools` implementation and before publication.

## Tools

- `sync_gate`
- `publish`

## Rules

- Normal order is `sync_gate(stage="start")`, implementation, commit, `sync_gate(stage="finish", push=true)`.
- Finish/push and publish are mutating and require owner approval, `confirm_mutation=true`, and `issue_context="INT-*"`.
- Do not filter or stash prepared publication state during explicit publication unless owner instructs it.
- If start gate is bypassed by owner, record the exception in handoff.

## Blockers

- Dirty tree at start without owner override.
- Local commits missing `INT-*`.
- Push/publication requested while gates fail.

## Fallback

Direct scripts are fallback only after MCP blocker and owner approval.

## Examples

- Start: `sync_gate(cwd="D:/int/tools", stage="start", issue_context="INT-226")`
- Finish: `sync_gate(cwd="D:/int/tools", stage="finish", push=true, confirm_mutation=true, issue_context="INT-226")`
- Publish: `publish(cwd="D:/int/tools", target="tools", confirm_mutation=true, issue_context="INT-226")`
