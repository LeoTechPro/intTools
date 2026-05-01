---
name: doctor-status
description: intDBA doctor/status. Используйте для read-only проверки профилей, состояния подключения и безопасной диагностики intDBA.
---

# intDBA doctor/status

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.
- Read-only subcommands: `--help`, `doctor`, `migrate status`.

## Tool cards

### intdata_cli
    - Когда: нужно выполнить intDBA command-router subcommand.
    - Required inputs: `command`
    - Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `profile`, `args`
    - Режим: read-only by default
    - Approval / issue requirements: Read-only subcommands без approval; apply/dump/restore/local-test требуют owner approval, `issue_context=INT-*` и безопасный disposable/local target.
    - Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
    - Пример вызова: `{"name":"intdata_cli","arguments":{"command": "dba", "profile": "intdata-dev-ro", "args": ["doctor"]}}`
    - Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
- Subcommand cards: `doctor/status` read-only; `migrate status` read-only; `migrate apply`, SQL apply, dump/restore/clone/copy/local-test mutating и запрещены unattended.
