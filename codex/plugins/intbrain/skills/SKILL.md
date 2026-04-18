---
name: intbrain
description: Работай с intData Brain через MCP-инструменты плагина: импорт PM/PARA данных и синхронизация runtime jobs.
---

# intData Brain

Используй этот skill, когда задача явно относится к intData Brain: импорт данных из vault, синхронизация runtime jobs, подготовка PM/PARA контекста или перенос runtime-состояния в IntBrain.

## Инструменты

- `intbrain_import_vault_pm`: импортирует PM/PARA данные из vault. Требует `owner_id`, `source_root`; `timezone` указывай явно, если она важна для дат.
- `intbrain_jobs_sync_runtime`: синхронизирует runtime jobs в IntBrain. Требует `owner_id`; `runtime_url` и `source_root` задавай только когда они известны из задачи или локального контекста.

## Правила выполнения

- Не вызывай локальные CLI или скрипты напрямую, если доступен MCP-инструмент этого плагина.
- Перед импортом или синхронизацией проверь owner/task context и не подставляй `owner_id` по догадке.
- Операции импорта и синхронизации считаются изменяющими состояние: выполняй их только при явном запросе владельца или в рамках подтверждённого Multica issue.
- Если не хватает `owner_id`, `source_root` или runtime source, остановись и зафиксируй конкретный blocker.
