---
name: vault-maintenance
description: Runtime vault maintenance. Используйте для vault sanitize и runtime vault GC workflow.
---

# Runtime vault maintenance

## When to use
- Use for approved runtime vault sanitize or garbage-collection maintenance.

## Do first
- Confirm the maintenance target and whether the request is sanitize or GC.
- Prefer the runtime MCP tools.
- Summarize affected scope, dry-run results, and applied maintenance status.

## Expected result
- The requested vault maintenance action is performed on the intended runtime scope.

## Checks
- Mutating maintenance includes approval and `issue_context=INT-*`.
- Dry-run is used when the scope is uncertain.
- The vault target is explicit.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The request would mutate state without approval.
- The target vault scope is ambiguous.

## Ask user when
- The maintenance target or blast radius is unclear.
- GC or sanitize would remove data outside the stated scope.

## Tool map
- `intdata_vault_sanitize`: mutating sanitize operation; approval required.
- `intdata_runtime_vault_gc`: mutating vault GC; prefer dry-run first when scope is unclear.
