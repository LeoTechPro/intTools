---
name: people-graph-policies
description: IntBrain people, graph и policies. Используйте для people resolve/get, graph neighbors и policy reads/upserts.
---

# IntBrain people, graph, and policies

## When to use
- Use for people resolution, entity lookup, graph neighbors, and policy reads or writes.

## Do first
- Confirm `owner_id` and the target person, entity, or policy scope.
- Prefer the IntBrain MCP tools.
- Summarize resolved entity ids, neighbor sets, and policy read or write status.

## Expected result
- The requested people, graph, or policy operation is performed on one clear owner scope.

## Checks
- `owner_id` is known.
- Entity ids, chat ids, or query strings are explicit when required.
- Mutating policy writes include approval and `issue_context=INT-*`.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The task needs mutation without approval.
- Person, entity, or policy scope is ambiguous.

## Ask user when
- More than one identity or chat target could match.
- Policy semantics are unclear or broader than the user request.

## Tool map
- `intbrain_people_resolve`: read-only; inputs `owner_id`, `q`; optional `limit`.
- `intbrain_people_get`: read-only; inputs `owner_id`, `entity_id`.
- `intbrain_graph_neighbors`: read-only; inputs `owner_id`, `entity_id`; optional `depth`, `limit`, `link_type`.
- `intbrain_people_policy_tg_get`: read-only Telegram policy lookup for a person.
- `intbrain_group_policy_get`: read-only; inputs `owner_id`, `chat_id`.
- `intbrain_group_policy_upsert`: mutating; inputs `confirm_mutation`, `issue_context`, `owner_id`, `chat_id`, `respond_mode`, `access_mode`, `tools_policy`; optional metadata.
- `intbrain_policy_events_list`: read-only; input `owner_id`; optional `since`, `limit`.
