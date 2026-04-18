---
name: intdata-runtime-vault-maintenance
description: Use for intData Runtime vault sanitizer and runtime vault garbage collection workflows.
---

# intData Runtime: Vault Maintenance

Use this for vault cleanup only when the task explicitly targets vault/runtime hygiene.

## Tools

- `intdata_vault_sanitize`
- `intdata_runtime_vault_gc`

## Rules

- Default to `dry_run=true`.
- Non-dry-run requires `confirm_mutation=true`, `issue_context="INT-*"`, and owner approval for the concrete target.
- Never move secrets into tracked git.

## Blockers

- Missing safe target or dry-run output.
- Tool would delete or rewrite unknown runtime state.
- No explicit owner approval for non-dry-run.

## Fallback

Direct vault scripts require MCP blocker and owner approval.

## Examples

- Sanitize dry-run: `intdata_vault_sanitize(cwd="D:/int/tools", dry_run=true)`
- GC dry-run: `intdata_runtime_vault_gc(cwd="D:/int/tools", dry_run=true)`
- Apply: `intdata_vault_sanitize(cwd="D:/int/tools", dry_run=false, confirm_mutation=true, issue_context="INT-226")`
