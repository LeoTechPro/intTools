---
name: intbrain-cabinet-absorption
description: Use for Cabinet inventory and dry-run/import absorption into IntBrain without reviving Cabinet as a standalone plugin surface.
---

# IntBrain: Cabinet Absorption

Use this only for Cabinet-to-IntBrain absorption work.

## Tools

- `intbrain_cabinet_inventory`
- `intbrain_cabinet_import`

## Rules

- Cabinet is source/import surface; IntBrain remains canonical.
- Start with inventory and `dry_run=true`.
- Non-dry-run import requires `owner_id`, `confirm_mutation=true`, `issue_context="INT-*"`, and owner approval.
- Do not add new active `cabinet_*` plugin surfaces.

## Blockers

- Cabinet root unknown.
- Owner has not accepted source-of-truth and import scope.
- Task requests deleting Cabinet before migration acceptance.

## Fallback

Direct Cabinet import scripts require MCP blocker and owner approval.

## Examples

- Inventory: `intbrain_cabinet_inventory(cabinet_root="D:/int/cabinet", limit=100)`
- Dry-run import: `intbrain_cabinet_import(cabinet_root="D:/int/cabinet", dry_run=true, limit=100)`
- Apply: `intbrain_cabinet_import(owner_id=1, cabinet_root="D:/int/cabinet", dry_run=false, confirm_mutation=true, issue_context="INT-226")`
