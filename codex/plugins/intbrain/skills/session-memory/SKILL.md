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
- Required inputs: `codex_home`
- Optional/schema inputs: `state_path`, `source_root`, `days`, `limit`, `repo`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. `codex_home` должен быть указан явно владельцем или задачей; implicit probing native Codex home запрещён. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_recent_work","arguments":{"codex_home":"D:/path/to/codex-home"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_memory_session_brief
- Когда: нужен brief по одной session.
- Required inputs: `session_id`, `codex_home`
- Optional/schema inputs: `state_path`, `source_root`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. `codex_home` должен быть указан явно владельцем или задачей; implicit probing native Codex home запрещён. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_session_brief","arguments":{"session_id":"session-id","codex_home":"D:/path/to/codex-home"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_memory_sync_sessions
- Когда: нужно dry-run или approved импортировать sessions memory.
- Required inputs: explicit `codex_home` или `file`
- Optional/schema inputs: `confirm_mutation`, `issue_context`, `owner_id`, `codex_home`, `state_path`, `source_root`, `since`, `file`, `incremental`, `dry_run`
- Режим: read-only by default
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена. Для dry-run тоже запрещён implicit probing native Codex home: источник должен быть явным.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_sync_sessions","arguments":{"codex_home":"D:/path/to/codex-home","dry_run":true}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
