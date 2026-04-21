---
name: sync-gate
description: Sync gate workflow. Use for start/finish repository synchronization checks and clean/ahead/upstream validation before closing work.
---

# Sync Gate

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.
- Local delivery publish wrappers removed: do not use `/int/tools/delivery/bin/publish_*`, `/int/tools/codex/bin/publish_*.ps1`, or an `intdata-control` `publish` tool.

## Tool cards

### sync_gate_start
- Когда: нужно выполнить обязательный start-gate перед tracked правками в `/int/*`.
- Required inputs: нет
- Optional/schema inputs: `cwd`, `timeout_sec`, `all_repos`, `root_path`
- Режим: read-only by default
- Approval / issue requirements: Не требуется для read-only start check. Если операция требует mutation или обходит blocker, остановиться и получить owner approval.
- Не использовать когда: нет нужного repo context, checkout не подтверждён, требуется hidden publish/deploy wrapper, или задача относится к Cabinet.
- Пример вызова: `{"name":"sync_gate_start","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### sync_gate_finish
- Когда: нужно выполнить finish-gate после локального commit и проверить clean/ahead/upstream состояние перед close-out.
- Required inputs: `confirm_mutation`, `issue_context`
- Optional/schema inputs: `cwd`, `timeout_sec`, `push`, `all_repos`, `root_path`
- Режим: mutating when `push=true`
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного repo context, checkout не подтверждён, требуется hidden publish/deploy wrapper, или задача относится к Cabinet.
- Пример вызова: `{"name":"sync_gate_finish","arguments":{"confirm_mutation": true, "issue_context": "INT-258", "push": true}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
