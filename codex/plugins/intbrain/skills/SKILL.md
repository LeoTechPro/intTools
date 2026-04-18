---
name: intbrain
description: Работай с intData Brain через MCP-инструменты плагина: контекст, память, Cabinet import, PM/PARA и runtime jobs.
---

# intData Brain

Используй этот skill, когда задача явно относится к intData Brain: контекст-паки, agent memory, Cabinet absorption/import, импорт данных из vault, синхронизация runtime jobs, подготовка PM/PARA контекста или перенос runtime-состояния в IntBrain.

## Capability skills

- `intbrain-context-memory`: context pack/search/store and graph links.
- `intbrain-people-graph-policies`: people, graph, Telegram and group policy tools.
- `intbrain-jobs-pm`: jobs, PM dashboard, task and constraint tools.
- `intbrain-memory-imports`: Codex/OpenClaw session and MemPalace imports.
- `intbrain-cabinet-absorption`: Cabinet inventory/import into IntBrain.

## Инструменты

- `intbrain_import_vault_pm`: импортирует PM/PARA данные из vault. Требует `owner_id`, `source_root`; `timezone` указывай явно, если она важна для дат.
- `intbrain_jobs_sync_runtime`: синхронизирует runtime jobs в IntBrain. Требует `owner_id`; `runtime_url` и `source_root` задавай только когда они известны из задачи или локального контекста.
- `intbrain_memory_sync_sessions`: dry-run/import Codex/OpenClaw session JSONL memory into IntBrain.
- `intbrain_memory_import_mempalace`: dry-run/import MemPalace palace data into IntBrain.
- `intbrain_cabinet_inventory`: count-check Cabinet workspace/runtime data before product absorption.
- `intbrain_cabinet_import`: dry-run/import Cabinet workspace/runtime data into IntBrain.

## Правила выполнения

- Не вызывай локальные CLI или скрипты напрямую, если доступен MCP-инструмент этого плагина.
- Перед импортом или синхронизацией проверь owner/task context и не подставляй `owner_id` по догадке.
- Операции импорта и синхронизации считаются изменяющими состояние: выполняй их только при явном запросе владельца или в рамках подтверждённого Multica issue.
- Если не хватает `owner_id`, `source_root` или runtime source, остановись и зафиксируй конкретный blocker.
- Cabinet больше не должен подключаться как отдельный active plugin surface; используйте IntBrain Cabinet tools.
