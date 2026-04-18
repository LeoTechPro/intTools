# IntBrain external imports

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intbrain_import_vault_pm
- Когда: нужно импортировать PM/PARA из vault.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`, `source_root`
- Optional/schema inputs: `timezone`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_import_vault_pm","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1, "source_root": "D:/int/tools"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_memory_import_mempalace
- Когда: нужно dry-run или approved импортировать MemPalace data.
- Required inputs: `palace_root`
- Optional/schema inputs: `confirm_mutation`, `issue_context`, `owner_id`, `codex_home`, `state_path`, `limit`, `dry_run`
- Режим: read-only by default
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_memory_import_mempalace","arguments":{"palace_root": "D:/int/mempalace"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
