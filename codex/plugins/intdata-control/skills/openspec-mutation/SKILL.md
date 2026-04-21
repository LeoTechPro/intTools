---
name: openspec-mutation
description: OpenSpec lifecycle mutations. Используйте только когда есть owner-approved SPEC-MUTATION scope для создания, изменения, архивации или mutating exec операций OpenSpec.
---

# OpenSpec lifecycle mutations

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### openspec_archive
- Когда: нужно архивировать завершённый approved change.
- Required inputs: `confirm_mutation`, `issue_context`, `change_name`
- Optional/schema inputs: `cwd`, `timeout_sec`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"openspec_archive","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "change_name": "agent-tool-plane-v1"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### openspec_change_mutate
- Когда: нужно выполнить mutating `openspec change <subcommand>`.
- Required inputs: `confirm_mutation`, `issue_context`, `subcommand`
- Optional/schema inputs: `cwd`, `timeout_sec`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нужен read-only `list/show/get`; используй `openspec_list`, `openspec_show`, `openspec_status` или `openspec_validate`.
- Пример вызова: `{"name":"openspec_change_mutate","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "subcommand": "set", "args": ["agent-tool-plane-v1"]}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### openspec_spec_mutate
- Когда: нужно выполнить mutating `openspec spec <subcommand>`.
- Required inputs: `confirm_mutation`, `issue_context`, `subcommand`
- Optional/schema inputs: `cwd`, `timeout_sec`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нужен read-only `list/show/get`; используй read-only OpenSpec tools.
- Пример вызова: `{"name":"openspec_spec_mutate","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "subcommand": "set", "args": ["process"]}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### openspec_new
- Когда: нужно создать новый OpenSpec change после owner approval.
- Required inputs: `confirm_mutation`, `issue_context`
- Optional/schema inputs: `cwd`, `timeout_sec`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: задача ещё в PLAN/аудите или нет согласованного scope.
- Пример вызова: `{"name":"openspec_new","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "args": ["my-change-id"]}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### openspec_exec_mutate
- Когда: нужен редкий mutating OpenSpec fallback через allowlisted args.
- Required inputs: `confirm_mutation`, `issue_context`, `args`
- Optional/schema inputs: `cwd`, `timeout_sec`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: существует явный read-only или lifecycle tool; emergency fallback не является обычным маршрутом.
- Пример вызова: `{"name":"openspec_exec_mutate","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "args": ["archive", "agent-tool-plane-v1"]}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
