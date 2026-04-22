---
name: codex
description: Codex usage, troubleshooting, and recovery workflows. Use for restoring hidden/archived local Codex sessions, locating Codex storage on disk, explaining Codex CLI/VS Code behavior, and referencing official OpenAI Codex documentation.
metadata:
  knowledge_mode: hybrid-core-reference
  last_verified_at: "2026-02-25"
  refresh_interval_days: 30
  official_sources:
    - https://platform.openai.com/docs/codex
    - https://platform.openai.com/docs
---

# Codex

## Process Core (stable)
- Диагностика и восстановление локальных Codex-сессий выполняются non-destructive.
- Любые рискованные действия требуют backup/rollback шагов.
- Секреты и `.env` не редактируются в рамках troubleshooting.

## Overview
Recover local Codex sessions and map Codex storage/index files, with safe backup/rollback steps and links to official docs.

## Workflow Decision Tree

1) Need latest/official behavior or options? Read `references/codex-docs.md` and open the linked OpenAI docs.
2) Missing local session? Follow "Restore Local Session".
3) Need to undo changes? Follow "Rollback".

## Restore Local Session (non-destructive)

Goal: make a local session appear in Codex UI/CLI lists without losing data.

1) Identify session files
   - Active sessions live under `~/.codex/sessions/YYYY/MM/DD/*.jsonl`.
   - Archived sessions may live under `~/.codex/archived_sessions/*.jsonl`.

2) If session is archived
   - Copy (do NOT move) the archived JSONL into the matching date folder under `~/.codex/sessions/`.

3) Re-index for visibility
   - Append an entry to `~/.codex/session_index.jsonl` with:
     - `id` (from the session file's first line: `payload.id`)
     - `thread_name` (short human name)
     - `updated_at` (last timestamp in that session file)
   - Append a matching entry to `~/.codex/history.jsonl` with:
     - `session_id` (same id)
     - `ts` (unix seconds of updated_at)
     - `text` (short name)

4) Refresh UI/CLI
   - Restart the Codex panel in VS Code or rerun `codex resume`.

## Rollback

If the session list breaks or looks wrong:
1) Restore from backups of `~/.codex/session_index.jsonl` and `~/.codex/history.jsonl`.
2) Remove any copied session files that should not be active.
3) Restart VS Code or re-run `codex resume`.

## Safety Notes

- Always backup index files before editing.
- Prefer copy over move for archived sessions.
- Never edit secrets or `.env` while troubleshooting.

## Resources

### references/
- `codex-docs.md`: official OpenAI Codex docs links + short summaries.

## Volatile References (on-demand)
- Флаги CLI, поведение UI, и changelog считаются volatile; проверяй по официальной документации в момент задачи.

## Freshness Gate
- Если прошло больше `refresh_interval_days`, не полагайся на локальные примеры без on-demand проверки по `official_sources`.
