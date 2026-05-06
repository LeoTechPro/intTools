---
name: coordctl
description: Standalone coordctl skill for Git-aware coordination of parallel agent edits. Use when Codex needs to start sessions, acquire file/hunk edit intents, heartbeat, inspect status, release, cleanup worktrees/branches, run GC, or dry-run merges before tracked mutations.
---

# coordctl

- Prefer the standalone `mcp__coordctl__coordctl_*` tools when available.
- If only `intdata-control` is loaded, use `mcp__intdata_control__coordctl_*`; it is the compatibility surface.
- Use shell fallback only when MCP tools are unavailable: `python D:\int\tools\coordctl\coordctl.py ...`.
- Do not use `lockctl` as a default fallback. It remains a repo-retained legacy CLI for manual diagnostics only with direct owner approval.

## Required discipline

- Start a session for every branch/worktree that will edit tracked files.
- Acquire an intent before writing a file region.
- Prefer `region_kind=hunk` with base-bound `region_id` ranges; use `file` for dangerous or unstructured files.
- Run `coordctl_status` before integrating branches.
- Run `coordctl_merge_dry_run` before merge/push decisions.
- End every session with `coordctl_cleanup` or `coordctl_release`; use `delete_worktree` and `delete_branch` only when that cleanup is approved and safe.
- Treat `COORD_CONFLICT` and `STALE_BASE` as blockers that require owner decision instead of overwriting another branch.

## Tool cards

### coordctl_session_start
- Когда: начать Git-aware coordination session для owner/branch/base.
- Required inputs: `repo_root`, `owner`, `branch`, `base`
- Optional/schema inputs: `issue`, `worktree_path`, `lease_sec`
- Режим: mutating
- Approval / issue requirements: Требуется owner approval для tracked-work coordination; `issue` optional metadata. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: branch/base неизвестны или repo_root не подтвержден.
- Пример вызова: `{"name":"coordctl_session_start","arguments":{"repo_root":"D:/int/tools","owner":"codex:task","branch":"agent/task/a","base":"main"}}`
- Fallback/blocker: если base stale или session не создать, остановиться и запросить rebase/refresh decision.

### coordctl_intent_acquire
- Когда: взять или продлить intent lease на file/hunk/symbol region перед tracked-правкой.
- Required inputs: `repo_root`, `path`, `owner`, `base`, `region_kind`, `region_id`
- Optional/schema inputs: `issue`, `lease_sec`, `session_id`
- Режим: mutating
- Approval / issue requirements: Требуется owner approval для tracked mutations; `issue` optional metadata. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: region нельзя описать или base не совпадает с branch history.
- Пример вызова: `{"name":"coordctl_intent_acquire","arguments":{"repo_root":"D:/int/tools","path":"README.md","owner":"codex:task","base":"main","region_kind":"hunk","region_id":"12:18"}}`
- Fallback/blocker: `COORD_CONFLICT` и `STALE_BASE` не обходить; остановиться и спросить владельца.

### coordctl_status
- Когда: read-only посмотреть active/final sessions и leases.
- Required inputs: `repo_root`
- Optional/schema inputs: `path`, `owner`, `issue`, `all`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only.
- Не использовать когда: repo_root неизвестен.
- Пример вызова: `{"name":"coordctl_status","arguments":{"repo_root":"D:/int/tools","all":true}}`
- Fallback/blocker: если status недоступен, не начинать tracked mutation.

### coordctl_heartbeat
- Когда: продлить active session и связанные leases.
- Required inputs: `session_id`
- Optional/schema inputs: `lease_sec`
- Режим: mutating
- Approval / issue requirements: Разрешено для своей active session with owner approval; if the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: session_id неизвестен или session принадлежит другому owner.
- Пример вызова: `{"name":"coordctl_heartbeat","arguments":{"session_id":"<session-id>","lease_sec":3600}}`
- Fallback/blocker: если heartbeat не прошел, проверить status и не продолжать запись вслепую.

### coordctl_release
- Когда: снять sessions/leases по `session_id` или `issue`.
- Required inputs: нет
- Optional/schema inputs: `session_id`, `repo_root`, `issue`
- Режим: mutating
- Approval / issue requirements: Разрешено для своей session; issue-wide release требует owner approval. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: selector может зацепить чужую active работу.
- Пример вызова: `{"name":"coordctl_release","arguments":{"session_id":"<session-id>"}}`
- Fallback/blocker: если selector неоднозначен, сначала вызвать `coordctl_status`.

### coordctl_cleanup
- Когда: dry-run/apply cleanup session, включая optional branch/worktree cleanup.
- Required inputs: `session_id`
- Optional/schema inputs: `final_state`, `delete_worktree`, `delete_branch`, `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: `dry_run` безопасен; `apply` с удалением worktree/branch требует owner approval. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: branch не merged/released/abandoned явно.
- Пример вызова: `{"name":"coordctl_cleanup","arguments":{"session_id":"<session-id>","final_state":"released","dry_run":true}}`
- Fallback/blocker: сначала dry-run; apply только после понятного списка удаляемого.

### coordctl_gc
- Когда: dry-run или удалить expired/final runtime rows.
- Required inputs: нет
- Optional/schema inputs: `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: `dry_run` безопасен; `apply` требует owner approval. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: есть сомнение, что active session могла быть ошибочно expired.
- Пример вызова: `{"name":"coordctl_gc","arguments":{"dry_run":true}}`
- Fallback/blocker: не чистить вручную SQLite/runtime files.

### coordctl_merge_dry_run
- Когда: проверить Git merge двух refs без изменения tracked files.
- Required inputs: `repo_root`, `target`, `branch`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only.
- Не использовать когда: refs неизвестны или repo_root не подтвержден.
- Пример вызова: `{"name":"coordctl_merge_dry_run","arguments":{"repo_root":"D:/int/tools","target":"main","branch":"agent/task/a"}}`
- Fallback/blocker: при конфликте не merge; остановиться и запросить решение.
