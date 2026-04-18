---
name: intdb-sql-apply
description: Use for owner-gated SQL execution, file apply, dump, restore, clone, and copy operations through intdb.
---

# intdb: SQL Apply

Use this only for explicit SQL/apply/dump/restore/clone/copy tasks.

## Tools

- `intdata_cli`

## Rules

- Treat SQL execution, file apply, dump, restore, clone, and copy as high-risk.
- Require `confirm_mutation=true`, `issue_context="INT-*"`, explicit target profile, and owner approval.
- Never guess credentials, profile, host, or env.

## Blockers

- Missing approved SQL/source file.
- Missing profile or secret.
- No rollback/backup plan for destructive operation.

## Fallback

No direct SQL shell fallback without owner approval.

## Examples

- Plan only: `intdata_cli(command="intdb", args=["sql", "--help"])`
- Apply file: `intdata_cli(command="intdb", args=["apply", "path/to/file.sql"], confirm_mutation=true, issue_context="INT-226")`
