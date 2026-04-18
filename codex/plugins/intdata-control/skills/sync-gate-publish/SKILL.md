# Sync gate и publication

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### sync_gate
- Когда: нужно выполнить governed git sync-gate start/finish.
- Required inputs: `stage`
- Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `push`, `all_repos`, `root_path`
- Режим: read-only by default
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"sync_gate","arguments":{"stage": "start"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### publish
- Когда: нужно выполнить approved publication/deploy flow.
- Required inputs: `confirm_mutation`, `issue_context`, `target`
- Optional/schema inputs: `cwd`, `timeout_sec`, `no_push`, `no_deploy`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"publish","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "target": "tools"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
