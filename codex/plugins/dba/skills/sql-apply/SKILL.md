---
name: sql-apply
description: dba SQL/apply. Используйте для controlled SQL execution/apply workflows с read-only defaults и отдельными gates для writes.
---

# intDBA SQL/apply

- `intdata_cli` является command-router; выбирай subcommand по этой карточке, а не угадывай shell-команду.
- Use only for planning SQL/apply. Live apply is forbidden unattended.

## Tool cards

### intdata_cli
    - Когда: нужно выполнить intDBA command-router subcommand.
    - Required inputs: `command`
    - Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `args`
    - Режим: read-only by default
    - Approval / issue requirements: Read-only subcommands без approval; apply/dump/restore/local-test требуют owner approval, `issue_context=INT-*` и безопасный disposable/local target.
    - Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
    - Пример вызова: `{"name":"intdata_cli","arguments":{"command": "dba", "args": ["doctor", "status"]}}`
    - Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
- Subcommand cards: `doctor/status` read-only; `migrate status` read-only; `migrate apply`, SQL apply, dump/restore/clone/copy/local-test mutating и запрещены unattended.
