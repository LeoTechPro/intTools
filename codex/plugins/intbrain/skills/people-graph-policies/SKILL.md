---
name: people-graph-policies
description: IntBrain people, graph и policies. Используйте для people resolve/get, graph neighbors и policy reads/upserts.
---

# IntBrain people, graph и policies

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intbrain_people_resolve
- Когда: нужно найти людей по query.
- Required inputs: `owner_id`, `q`
- Optional/schema inputs: `limit`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_people_resolve","arguments":{"owner_id": 1, "q": "Иван"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_people_get
- Когда: нужно получить профиль person/entity.
- Required inputs: `owner_id`, `entity_id`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_people_get","arguments":{"owner_id": 1, "entity_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_graph_neighbors
- Когда: нужно получить соседей графа.
- Required inputs: `owner_id`, `entity_id`
- Optional/schema inputs: `depth`, `limit`, `link_type`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_graph_neighbors","arguments":{"owner_id": 1, "entity_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_people_policy_tg_get
- Когда: нужна effective Telegram policy по tg_user_id.
- Required inputs: `owner_id`, `tg_user_id`
- Optional/schema inputs: `chat_id`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_people_policy_tg_get","arguments":{"owner_id": 1, "tg_user_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_group_policy_get
- Когда: нужна group policy по chat_id.
- Required inputs: `owner_id`, `chat_id`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_group_policy_get","arguments":{"owner_id": 1, "chat_id": "-1000000000000"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_group_policy_upsert
- Когда: нужно записать group policy.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`, `chat_id`, `respond_mode`, `access_mode`, `tools_policy`
- Optional/schema inputs: `name`, `project_scope`, `notes`, `metadata`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_group_policy_upsert","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1, "chat_id": "-1000000000000", "respond_mode": "manual", "access_mode": "restricted", "tools_policy": "read_only"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_policy_events_list
- Когда: нужно посмотреть policy events/provenance.
- Required inputs: `owner_id`
- Optional/schema inputs: `since`, `limit`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_policy_events_list","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
