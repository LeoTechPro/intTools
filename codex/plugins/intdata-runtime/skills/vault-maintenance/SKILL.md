# Runtime vault maintenance

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intdata_vault_sanitize
- Когда: нужно проверить или выполнить vault sanitize.
- Required inputs: нет
- Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `dry_run`, `args`
- Режим: read-only by default
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"intdata_vault_sanitize","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intdata_runtime_vault_gc
- Когда: нужно проверить или выполнить runtime vault GC.
- Required inputs: нет
- Optional/schema inputs: `cwd`, `timeout_sec`, `confirm_mutation`, `issue_context`, `dry_run`, `args`
- Режим: read-only by default
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"intdata_runtime_vault_gc","arguments":{}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
