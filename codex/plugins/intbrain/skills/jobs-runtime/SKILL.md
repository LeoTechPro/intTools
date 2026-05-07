---
name: jobs-runtime
description: IntBrain jobs runtime. Используйте для read-only просмотра jobs, job policies и runtime sync, а также для owner-approved policy upserts.
---

# IntBrain jobs runtime

## When to use
- Use for job listing, job inspection, runtime sync, and approved job policy writes.

## Do first
- Confirm `owner_id`, job id if applicable, and whether the task is read-only or mutating.
- Prefer the IntBrain MCP tools.
- Summarize returned job ids, sync result, or policy write status.

## Expected result
- The requested job or job policy operation is completed for a clear owner scope.

## Checks
- `owner_id` is known.
- Mutating policy writes include approval and `issue_context=INT-*`.
- Sync requests are explicitly intended, not assumed from a read-only question.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The request needs mutation without approval.
- Job id or target policy scope is unclear.

## Ask user when
- More than one job or owner could match the request.
- A job policy write changes behavior beyond the stated scope.

## Tool map
- `intbrain_jobs_list`: read-only list by owner and optional filters.
- `intbrain_jobs_get`: read-only job inspection by owner and job id.
- `intbrain_jobs_sync_runtime`: mutating runtime sync; approval required.
- `intbrain_job_policy_upsert`: mutating policy write; approval required.
