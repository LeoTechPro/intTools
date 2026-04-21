---
name: context-memory
description: IntBrain context и memory. Используйте для context packs, memory search/store и graph links через canonical IntBrain tools.
---

# IntBrain context и memory

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intbrain_context_pack
- Когда: нужно получить context pack из IntBrain.
- Required inputs: `owner_id`
- Optional/schema inputs: `entity_id`, `query`, `limit`, `depth`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_context_pack","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_memory_search
- Когда: нужно найти импортированную память по query.
- Required inputs: `owner_id`, `query`
- Optional/schema inputs: `limit`, `days`, `repo`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_search","arguments":{"owner_id": 1, "query": "текущий контекст"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_context_store
- Когда: нужно записать context item в IntBrain.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`, `kind`, `title`, `text_content`
- Optional/schema inputs: `entity_id`, `source_path`, `source_hash`, `chunk_kind`, `tags`, `source`, `priority`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_context_store","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1, "kind": "note", "title": "Проверка", "text_content": "Текст контекста"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_graph_link
- Когда: нужно создать или обновить typed graph edge.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`, `from_entity_id`, `to_entity_id`, `link_type`
- Optional/schema inputs: `weight`, `confidence`, `source`, `source_path`, `metadata`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_graph_link","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1, "from_entity_id": 1, "to_entity_id": 1, "link_type": "related"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
