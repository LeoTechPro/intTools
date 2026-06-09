---
name: coordctl
description: Standalone coordctl skill for Git-aware coordination of parallel agent edits. Use when Codex needs to begin/record sessions, record file/hunk edit intents, heartbeat, inspect status, release, cleanup worktrees/branches, run GC, or dry-run merges. coordctl is advisory provenance, not a permission gate.
---

# coordctl

- Prefer the standalone `mcp__coordctl__coordctl_*` tools when available.
- If only `intdata-control` is loaded, use `mcp__intdata_control__coordctl_*`; it is the compatibility surface.
- Use shell fallback only when MCP tools are unavailable: `python /int/tools/coordctl/coordctl.py ...` (Windows: `D:\int\tools\coordctl\coordctl.py`).
- Active project coordination runtime is `coordctl` only; do not use retired coordination tools as fallback.

## Discipline (advisory, non-blocking)

coordctl is **mandatory by rule, non-blocking by mechanics**: record presence/intent
cheaply and always; the tool never refuses a write. Formula: **tool = always-write +
warn, agent = stop-on-real-overlap**.

- Begin work with `coordctl_begin` (or `coordctl_session_start`) for every branch/worktree that edits tracked files; record an intent per edited file/region.
- Prefer `region_kind=hunk` with base-bound `region_id` ranges; use `file` for unstructured files.
- `COORD_OVERLAP` and `STALE_BASE_OBSERVED` are warnings/observations, not refusals. On a real overlap with another active owner on the same region, stop and coordinate with the owner — but never overwrite, revert, stash or clean another agent's work to force a clean tree.
- Run `coordctl_status` before integrating branches and `coordctl_merge_dry_run` before merge/push decisions.
- End sessions with `coordctl_release` (or `coordctl_cleanup`).
- Owner approval is required ONLY for destructive maintenance (`coordctl_cleanup` with `delete_worktree`/`delete_branch`, `coordctl_gc --apply`) — never for ordinary session/begin/intent/heartbeat/release writes.

## Tool cards

### coordctl_session_start
- Когда: начать Git-aware coordination session для owner/branch/base.
- Required inputs: `repo_root`, `owner`, `branch`, `base`
- Optional/schema inputs: `issue`, `worktree_path`, `lease_sec`
- Режим: advisory
- Approval / issue requirements: Approval не требуется — это координационная запись присутствия. `issue` optional metadata.
- Не использовать когда: branch/base неизвестны или repo_root не подтвержден (в этом случае удобнее `coordctl_begin`).
- Пример вызова: `{"name":"coordctl_session_start","arguments":{"repo_root":"/int/tools","owner":"codex:task","branch":"agent/task/a","base":"main"}}`
- Fallback/blocker: если base не резолвится, остановиться и запросить refresh; overlap — не блокер.

### coordctl_begin
- Когда: дешёвый non-blocking старт работы — открыть session (и optional coarse file intent) с autodetect repo/branch/base.
- Required inputs: нет
- Optional/schema inputs: `repo_root`, `owner`, `issue`, `branch`, `base`, `path`, `worktree_path`, `lease_sec`
- Режим: advisory
- Approval / issue requirements: Approval не требуется — координационная запись присутствия. `owner` берётся из аргумента или `$COORDCTL_OWNER`.
- Не использовать когда: cwd не внутри git-репозитория (тогда задать `repo_root`).
- Пример вызова: `{"name":"coordctl_begin","arguments":{"owner":"codex:task","path":"README.md"}}`
- Fallback/blocker: никогда не падает из-за overlap; overlap возвращается как warning на intent.

### coordctl_intent_acquire
- Когда: записать или продлить intent на file/hunk region. Запись append-only: всегда успешна.
- Required inputs: `repo_root`, `path`, `owner`, `base`, `region_kind`, `region_id`
- Optional/schema inputs: `issue`, `lease_sec`, `session_id`
- Режим: advisory
- Approval / issue requirements: Approval не требуется — координационная запись. `issue` optional metadata.
- Не использовать когда: region нельзя описать корректно.
- Пример вызова: `{"name":"coordctl_intent_acquire","arguments":{"repo_root":"/int/tools","path":"README.md","owner":"codex:task","base":"main","region_kind":"hunk","region_id":"12:18"}}`
- Fallback/blocker: `COORD_OVERLAP`/`STALE_BASE_OBSERVED` — это warnings; запись всё равно проходит. На реальном overlap того же региона остановиться и спросить владельца, а не перезаписывать.

### coordctl_status
- Когда: read-only посмотреть active/final sessions и leases.
- Required inputs: `repo_root`
- Optional/schema inputs: `path`, `owner`, `issue`, `all`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only.
- Не использовать когда: repo_root неизвестен.
- Пример вызова: `{"name":"coordctl_status","arguments":{"repo_root":"/int/tools","all":true}}`
- Fallback/blocker: status — не permission gate, но часть дисциплины. Если он недоступен, зафиксировать это в closeout, не чистить и не перезаписывать чужое присутствие; при риске shared overlap остановиться и спросить владельца.

### coordctl_heartbeat
- Когда: продлить active session и связанные leases.
- Required inputs: `session_id`
- Optional/schema inputs: `lease_sec`
- Режим: advisory
- Approval / issue requirements: Approval не требуется для продления своей session.
- Не использовать когда: session_id неизвестен.
- Пример вызова: `{"name":"coordctl_heartbeat","arguments":{"session_id":"<session-id>","lease_sec":3600}}`
- Fallback/blocker: если heartbeat не прошёл, проверить status; не блокер.

### coordctl_release
- Когда: снять sessions/leases по `session_id`, `issue`, `lease_id`, `owner` или `path`.
- Required inputs: нет
- Optional/schema inputs: `session_id`, `repo_root`, `issue`, `lease_id`, `owner`, `path`
- Режим: advisory
- Approval / issue requirements: Approval не требуется для release своей работы. `--owner`/`--path`/`--issue` требуют `repo_root` как safety-scope.
- Не использовать когда: selector может зацепить чужую active работу без необходимости.
- Пример вызова: `{"name":"coordctl_release","arguments":{"repo_root":"/int/tools","lease_id":"<lease-id>"}}`
- Fallback/blocker: если selector неоднозначен, сначала вызвать `coordctl_status`.

### coordctl_cleanup
- Когда: dry-run/apply cleanup session, включая optional branch/worktree cleanup.
- Required inputs: `session_id`
- Optional/schema inputs: `final_state`, `delete_worktree`, `delete_branch`, `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: `dry_run` безопасен; `apply` с удалением worktree/branch — destructive maintenance, требует owner approval. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
- Не использовать когда: branch не merged/released/abandoned явно.
- Пример вызова: `{"name":"coordctl_cleanup","arguments":{"session_id":"<session-id>","final_state":"released","dry_run":true}}`
- Fallback/blocker: сначала dry-run; apply только после понятного списка удаляемого.

### coordctl_gc
- Когда: dry-run или удалить expired/final runtime rows.
- Required inputs: нет
- Optional/schema inputs: `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: `dry_run` безопасен; `apply` — destructive maintenance, требует owner approval. If the wrapper exposes guards, pass `confirm_mutation=true` and `issue_context=INT-*`.
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
- Пример вызова: `{"name":"coordctl_merge_dry_run","arguments":{"repo_root":"/int/tools","target":"main","branch":"agent/task/a"}}`
- Fallback/blocker: при конфликте не merge; остановиться и запросить решение.
