---
name: session-memory
description: IntBrain session memory. Используйте для session sync, recent work и session brief по canonical IntBrain tools.
---

# IntBrain session memory

## When to use
- Use for recent-work lookup, current session briefs, and approved session-memory sync.

## Do first
- Confirm `owner_id`, session scope, and whether the task is read-only or mutating.
- Prefer the IntBrain MCP tools.
- Summarize returned recent-work items, session briefs, or sync results.

## Expected result
- One clear session-memory action is completed for the intended owner scope.

## Checks
- `owner_id` is known.
- Read-only lookups stay read-only.
- Session sync includes approval and `issue_context=INT-*` when it mutates stored state.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The request needs mutation without approval.
- Session scope is ambiguous.

## Ask user when
- More than one session or owner could match.
- Sync semantics are unclear.

## Tool map
- `intbrain_memory_recent_work`: read-only recent work lookup.
- `intbrain_memory_session_brief`: read-only session brief.
- `intbrain_memory_sync_sessions`: mutating session sync; approval required.
