# Multica issue workflow

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### multica_issue
- Когда: Run structured `multica issue` commands.
- Required inputs: `command`
- Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `args`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"multica_issue","arguments":{"command": "status"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
