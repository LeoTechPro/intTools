---
name: pm-dashboard-tasks
description: IntBrain PM dashboard и tasks. Используйте для PM dashboard, tasks, PARA, health и constraints validation через IntBrain.
---

# IntBrain PM dashboard and tasks

## When to use
- Use for PM dashboard reads, task views, PARA, health, constraints validation, and approved task writes.

## Do first
- Confirm `owner_id`, timezone or date if needed, and whether the request is read-only or mutating.
- Prefer the IntBrain MCP tools.
- Summarize dashboard slices, task counts, constraint results, or created or patched task ids.

## Expected result
- The requested PM view or task mutation is completed for one clear owner scope.

## Checks
- `owner_id` is known.
- Read-only questions do not trigger task writes.
- Mutating task operations include approval and `issue_context=INT-*`.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The task needs mutation without approval.
- The intended task or owner scope is ambiguous.

## Ask user when
- More than one planning horizon, task id, or owner could match.
- Task create or patch fields imply broader product intent than stated.

## Tool map
- `intbrain_pm_dashboard`: read-only owner dashboard.
- `intbrain_pm_tasks`: read-only task view by owner.
- `intbrain_pm_para`: read-only PARA map.
- `intbrain_pm_health`: read-only PM health summary.
- `intbrain_pm_constraints_validate`: read-only 5-9 constraint validation.
- `intbrain_pm_task_create`: mutating task creation; approval required.
- `intbrain_pm_task_patch`: mutating task update; approval required.
