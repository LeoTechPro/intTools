---
name: sync-gate-publish
description: Sync gate и publication. Используйте для start/finish sync gates, governed publish flow и проверки clean/ahead/upstream состояния перед завершением.
---

# Sync gate и publication

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### sync_gate_start
- Когда: нужно выполнить governed git sync-gate start для текущего checkout.
- Required inputs: нет
- Optional/schema inputs: `cwd`, `timeout_sec`, `all_repos`, `root_path`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нужен finish/push; используй `sync_gate_finish`.
- Пример вызова: `{"name":"sync_gate_start","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### sync_gate_finish
- Когда: нужно выполнить governed git sync-gate finish; push разрешён только через этот tool.
- Required inputs: `confirm_mutation`, `issue_context`
- Optional/schema inputs: `cwd`, `timeout_sec`, `push`, `all_repos`, `root_path`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нужен start-gate; используй `sync_gate_start`.
- Пример вызова: `{"name":"sync_gate_finish","arguments":{"confirm_mutation": true, "issue_context": "INT-222", "push": true}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### publish
- Когда: нужно выполнить approved publication/deploy flow.
- Required inputs: `confirm_mutation`, `issue_context`, `target`
- Optional/schema inputs: `cwd`, `timeout_sec`, `no_push`, `no_deploy`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет explicit owner publish/deploy command.
- Пример вызова: `{"name":"publish","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "target": "tools"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
