---
name: migrations
description: intDB migrations. Используйте только для gated migration workflows, readiness checks и owner-approved apply paths.
---

# intDB migrations

- `intdata_cli` является command-router; выбирай subcommand по этой карточке, а не угадывай shell-команду.
- Use for migration review/status. `migrate apply` is mutating and requires approval.
- Для dev backend intdata с локальной Windows-машины не используйте `D:\int\data`; рабочий checkout находится на `agents@vds.intdata.pro:/int/data`.

## Tool cards

### intdata_cli
    - Когда: нужно выполнить intdb command-router subcommand.
    - Required inputs: `command`
    - Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `args`
    - Режим: read-only by default
    - Approval / issue requirements: Read-only subcommands без approval; apply/dump/restore/local-test требуют owner approval, `issue_context=INT-*` и безопасный disposable/local target.
    - Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
    - Пример вызова: `{"name":"intdata_cli","arguments":{"command": "intdb", "args": ["doctor", "status"]}}`
    - Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
- Subcommand cards: `doctor/status` read-only; `migrate status` read-only; `migrate apply`, SQL apply, dump/restore/clone/copy/local-test mutating и запрещены unattended.
