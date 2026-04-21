---
name: jobs-runtime
description: IntBrain jobs runtime. Используйте для read-only просмотра jobs, job policies и runtime sync операций IntBrain.
---

# IntBrain jobs runtime

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### intbrain_jobs_list
- Когда: нужно listing runtime jobs.
- Required inputs: `owner_id`
- Optional/schema inputs: `enabled`, `kind`, `limit`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_jobs_list","arguments":{"owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_jobs_get
- Когда: нужно details по job_id.
- Required inputs: `owner_id`, `job_id`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_jobs_get","arguments":{"owner_id": 1, "job_id": "job-id"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_jobs_sync_runtime
- Когда: нужно импортировать runtime jobs в IntBrain.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`
- Optional/schema inputs: `source_root`, `runtime_url`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_jobs_sync_runtime","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### intbrain_job_policy_upsert
- Когда: нужно записать policy override для job.
- Required inputs: `confirm_mutation`, `issue_context`, `owner_id`, `job_id`, `policy_mode`
- Optional/schema inputs: `notes`, `metadata`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён или требуется production/destructive действие без явной команды владельца.
- Пример вызова: `{"name":"intbrain_job_policy_upsert","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "owner_id": 1, "job_id": "job-id", "policy_mode": "read_only"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
