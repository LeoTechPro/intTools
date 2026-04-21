---
name: gate-receipts-commit-binding
description: Gate receipts и commit binding для intData Control. Используйте, когда нужно проверять gate status/receipts или связывать локальные коммиты с Multica issue и governance receipt.
---

# Gate receipts и commit binding

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### gate_status
- Когда: нужно read-only посмотреть receipts/bindings/approvals.
- Required inputs: нет
- Optional/schema inputs: `cwd`, `timeout_sec`, `repo_root`, `issue`, `receipt_id`, `commit`, `gate`, `owner`, `format`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"gate_status","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### gate_receipt
- Когда: нужно read-only открыть конкретный gate receipt.
- Required inputs: нет
- Optional/schema inputs: `cwd`, `timeout_sec`, `repo_root`, `receipt_id`, `commit`, `format`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"gate_receipt","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### commit_binding
- Когда: нужно привязать commit к gate/issue metadata.
- Required inputs: `confirm_mutation`, `issue_context`, `commit_sha`
- Optional/schema inputs: `cwd`, `timeout_sec`, `repo_root`, `issue`, `receipt_id`, `repo`, `post_issue`, `format`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"commit_binding","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "commit_sha": "0000000000000000000000000000000000000000"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
