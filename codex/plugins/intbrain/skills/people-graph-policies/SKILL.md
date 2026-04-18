---
name: intbrain-people-graph-policies
description: Use for IntBrain people resolution, graph neighbors, Telegram policy, and group policy tools.
---

# IntBrain: People, Graph, Policies

Use this when a task needs people/entity context, graph neighbors, Telegram policy, or group access policy.

## Tools

- `intbrain_people_resolve`
- `intbrain_people_get`
- `intbrain_graph_neighbors`
- `intbrain_people_policy_tg_get`
- `intbrain_group_policy_get`
- `intbrain_group_policy_upsert`
- `intbrain_policy_events_list`

## Rules

- Resolve before fetching a person if the entity id is not known.
- Policy reads are safe with known `owner_id` and ids.
- `group_policy_upsert` is a write and requires `confirm_mutation=true` and `issue_context="INT-*"`.

## Blockers

- Missing `owner_id`, entity id, `tg_user_id`, or `chat_id`.
- Ambiguous person resolution.
- No owner approval for policy write.

## Fallback

Direct IntBrain API calls require MCP blocker and owner approval.

## Examples

- Resolve: `intbrain_people_resolve(owner_id=1, q="Leonid", limit=5)`
- Graph: `intbrain_graph_neighbors(owner_id=1, entity_id=123, depth=1)`
- Group policy: `intbrain_group_policy_get(owner_id=1, chat_id="-100...")`
