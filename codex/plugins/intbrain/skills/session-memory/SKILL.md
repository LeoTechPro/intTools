---
name: session-memory
description: IntBrain session memory. Используйте для session sync, recent work и session brief по локальной Codex/OpenClaw памяти.
---

# IntBrain session memory

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intbrain_memory_recent_work
- Когда: нужно summary недавних локальных agent sessions.
- Required inputs: нет
- Optional/schema inputs: `codex_home`, `state_path`, `source_root`, `days`, `limit`, `repo`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_recent_work","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_memory_session_brief
- Когда: нужен brief по одной session.
- Required inputs: `session_id`
- Optional/schema inputs: `codex_home`, `state_path`, `source_root`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_session_brief","arguments":{"session_id": "session-id"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_memory_sync_sessions
- Когда: нужно dry-run или approved импортировать sessions memory.
- Required inputs: нет
- Optional/schema inputs: `confirm_mutation`, `issue_context`, `owner_id`, `codex_home`, `state_path`, `source_root`, `since`, `file`, `incremental`, `dry_run`
- Режим: read-only by default
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_sync_sessions","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
