---
name: context-memory
description: IntBrain context и memory. Используйте для context packs, memory search/store и graph links через canonical IntBrain tools.
---

# IntBrain context and memory

## When to use
- Use for context packs, imported memory lookup, context writes, and graph links.

## Do first
- Confirm `owner_id` and whether the request is read-only or mutating.
- Prefer the IntBrain MCP tools directly; do not replace policy errors with shell fallback.
- Summarize returned pack size, search hits, stored context ids, or graph-link results.

## Expected result
- The right memory or graph action is completed for one owner and one clear scope.

## Checks
- `owner_id` is known.
- Mutating calls include `confirm_mutation=true` and `issue_context=INT-*`.
- Context writes are justified by the user request, not by convenience.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The task needs mutation without approval.
- The owner or target entity is unclear.

## Ask user when
- More than one owner or target entity is plausible.
- A context write or graph link has unclear semantics.

## Tool map
- `intbrain_context_pack`: read-only; input `owner_id`; optional `entity_id`, `query`, `limit`, `depth`.
- `intbrain_memory_search`: read-only; inputs `owner_id`, `query`; optional `limit`, `days`, `repo`.
- `intbrain_context_store`: mutating; inputs `confirm_mutation`, `issue_context`, `owner_id`, `kind`, `title`, `text_content`; optional metadata fields.
- `intbrain_graph_link`: mutating; inputs `confirm_mutation`, `issue_context`, `owner_id`, `from_entity_id`, `to_entity_id`, `link_type`; optional relation metadata.
