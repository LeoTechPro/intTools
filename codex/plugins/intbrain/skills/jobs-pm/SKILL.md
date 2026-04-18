---
name: intbrain-jobs-pm
description: Use for IntBrain jobs, runtime job sync, PM dashboard, PM tasks, PARA, health, and constraints.
---

# IntBrain: Jobs and PM

Use this for IntBrain job inspection, PM/PARA views, and owner-approved task or job policy changes.

## Tools

- `intbrain_jobs_list`, `intbrain_jobs_get`, `intbrain_jobs_sync_runtime`
- `intbrain_job_policy_upsert`
- `intbrain_pm_dashboard`, `intbrain_pm_tasks`, `intbrain_pm_para`
- `intbrain_pm_health`, `intbrain_pm_constraints_validate`
- `intbrain_pm_task_create`, `intbrain_pm_task_patch`

## Rules

- Read dashboards, tasks, PARA, jobs, health, and constraints with known `owner_id`.
- Job sync, job policy upsert, task create, and task patch are writes/imports and require `confirm_mutation=true` and `issue_context="INT-*"`.
- Use explicit `timezone` for date-sensitive PM operations.

## Blockers

- Missing `owner_id`.
- Missing `job_id` or `task_id` for specific operations.
- No approval for writes/imports.

## Fallback

Direct API calls require MCP blocker and owner approval.

## Examples

- Jobs: `intbrain_jobs_list(owner_id=1, limit=20)`
- PM: `intbrain_pm_dashboard(owner_id=1, date="2026-04-18", timezone="Europe/Moscow")`
- Create task: `intbrain_pm_task_create(owner_id=1, title="...", confirm_mutation=true, issue_context="INT-226")`
