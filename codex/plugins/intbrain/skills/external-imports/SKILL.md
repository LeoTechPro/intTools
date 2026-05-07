---
name: external-imports
description: IntBrain external imports. Используйте для controlled импортов из vault/session/MemPalace в canonical IntBrain surfaces.
---

# IntBrain external imports

## When to use
- Use for controlled imports from approved external memory sources into IntBrain.

## Do first
- Confirm the import source, owner id, and whether the request is read-only planning or an approved mutation.
- Prefer the IntBrain import tools; do not improvise bulk shell ingestion.
- Summarize imported source, counts, and created records or blockers.

## Expected result
- The intended external memory source is imported into the correct IntBrain owner scope.

## Checks
- Import source and owner id are known.
- Mutating calls include explicit approval and `issue_context=INT-*`.
- The import scope is narrow enough to be intentional.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The import would mutate state without approval.
- Source path or import target is ambiguous.

## Ask user when
- The import source is not uniquely identified.
- The requested import is broader than the stated task.

## Tool map
- `intbrain_import_vault_pm`: mutating import from approved vault or PM sources.
- `intbrain_memory_import_mempalace`: mutating import from MemPalace into IntBrain memory.
