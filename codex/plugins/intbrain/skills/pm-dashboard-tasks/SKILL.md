---
name: pm-dashboard-tasks
description: IntBrain PM dashboard и tasks. Используйте для PM dashboard, tasks, PARA, health и constraints validation через IntBrain.
---

# IntBrain PM dashboard и tasks

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intbrain_pm_dashboard
- Когда: нужен PM dashboard по owner/date.
- Required inputs: `owner_id`
- Optional/schema inputs: `date`, `timezone`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_dashboard","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_pm_tasks
- Когда: нужно вывести PM tasks по view.
- Required inputs: `owner_id`
- Optional/schema inputs: `view`, `date`, `timezone`, `limit`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_tasks","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_pm_para
- Когда: нужна PARA map owner-а.
- Required inputs: `owner_id`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_para","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_pm_health
- Когда: нужны PM health metrics.
- Required inputs: `owner_id`
- Optional/schema inputs: `date`, `timezone`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_health","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_pm_constraints_validate
- Когда: нужно проверить PM 5-9 constraints.
- Required inputs: `owner_id`
- Optional/schema inputs: `date`, `timezone`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_constraints_validate","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_pm_task_create
- Когда: нужно создать PM task.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`, `title`
- Optional/schema inputs: `due_at`, `priority`, `energy_cost`, `project_entity_id`, `area_entity_id`, `goal_entity_id`, `okr_entity_id`, `key_result_entity_id`, `source_path`, `source_hash`, `active_pin`, `timezone`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_task_create","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1, "title": "Проверка"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_pm_task_patch
- Когда: нужно изменить PM task.
- Required inputs: `confirm_mutation`, `issue_context`, `task_id`, `owner_id`
- Optional/schema inputs: `title`, `status`, `due_at`, `priority`, `energy_cost`, `project_entity_id`, `area_entity_id`, `goal_entity_id`, `okr_entity_id`, `key_result_entity_id`, `active_pin`, `archive`, `timezone`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_pm_task_patch","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "task_id": 1, "owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
