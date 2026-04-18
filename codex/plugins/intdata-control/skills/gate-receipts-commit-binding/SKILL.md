---
name: intdata-control-gate-receipts-commit-binding
description: Use for gate status, gate receipts, and binding gate receipts to commits in intData Control.
---

# intData Control: Gate Receipts and Commit Binding

Use this after verification gates or when a commit must be linked to an approval/receipt.

## Tools

- `gate_status`
- `gate_receipt`
- `commit_binding`

## Rules

- Read gate status before binding.
- `commit_binding` is mutating and requires `confirm_mutation=true`, `issue_context="INT-*"`, and `commit_sha`.
- Every local commit for agent work must include the current `INT-*`.

## Blockers

- Missing receipt id or commit sha.
- Commit lacks `INT-*`.
- Gate status indicates failed or missing approval.

## Fallback

No direct fallback without recording MCP failure and owner approval.

## Examples

- Status: `gate_status(cwd="D:/int/tools", issue="INT-226", format="json")`
- Receipt: `gate_receipt(cwd="D:/int/tools", receipt_id="...")`
- Bind: `commit_binding(cwd="D:/int/tools", commit_sha="...", issue_context="INT-226", confirm_mutation=true)`
