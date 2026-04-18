---
name: intbrain-memory-imports
description: Use for importing or dry-running Codex/OpenClaw session memory and MemPalace data into IntBrain.
---

# IntBrain: Memory Imports

Use this for local session memory inventory/import and MemPalace migration into IntBrain.

## Tools

- `intbrain_memory_recent_work`
- `intbrain_memory_session_brief`
- `intbrain_memory_sync_sessions`
- `intbrain_memory_import_mempalace`
- `intbrain_import_vault_pm`

## Rules

- Start with recent work/session brief or `dry_run=true`.
- Non-dry-run imports and `intbrain_import_vault_pm` require `owner_id`, `confirm_mutation=true`, and `issue_context="INT-*"`.
- Scope imports with `source_root`, `since`, `file`, or `limit` when possible.

## Blockers

- Missing source path or session id.
- Missing `owner_id` for non-dry-run.
- Import would mix unrelated repo/session scope.

## Fallback

Direct file parsing/import scripts require MCP blocker and owner approval.

## Examples

- Recent work: `intbrain_memory_recent_work(source_root="D:/int/tools", days=7, limit=10)`
- Session brief: `intbrain_memory_session_brief(session_id="...")`
- Dry-run import: `intbrain_memory_sync_sessions(source_root="D:/int/tools", dry_run=true)`
