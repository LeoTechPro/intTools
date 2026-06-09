---
name: coordctl
description: Coordctl Git-aware coordination для параллельных agent edits. Используйте для begin/session, intent records, hunk-level coordination, heartbeat, release, status и merge dry-run как primary coordination runtime. coordctl — advisory provenance, не permission gate.
---

# coordctl: Git-aware coordination

- Используй эту capability-группу как primary coordination runtime для текущих проектов.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.
- MCP-first routing: use `mcp__intdata_control__coordctl_*` raw tools when available; if they are not visible, run `tool_search` for `coordctl` before shell fallback.
- Shell fallback is degraded mode only, because Codex shell sandbox may not have access to runtime coordination storage.
- coordctl — advisory: **mandatory by rule, non-blocking by mechanics**. Формула: **tool = always-write + warn, agent = stop-on-real-overlap**. `COORD_OVERLAP`/`STALE_BASE_OBSERVED` — это warnings, не отказ записи; на реальном overlap того же региона остановиться и скоординироваться с владельцем, не перезаписывая чужое.

## Tool cards

### coordctl_session_start
- Когда: нужно зарегистрировать agent/session branch перед file/hunk intent records.
- Required inputs: `repo_root`, `owner`, `branch`, `base`
- Optional/schema inputs: `issue`, `worktree_path`, `lease_sec`
- Режим: advisory
- Approval / issue requirements: Approval не требуется — это координационная запись присутствия, не high-risk mutation. `issue` optional metadata.
- Не использовать когда: нет подтвержденного repo/branch/base (удобнее `coordctl_begin`), или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_session_start","arguments":{"repo_root":"/int/tools","owner":"codex:session","branch":"agent/INT-1/a","base":"main"}}`
- Fallback/blocker: если base не резолвится, остановиться и запросить refresh; overlap — не блокер.

### coordctl_begin
- Когда: дешёвый non-blocking старт работы — open session (и optional coarse file intent) с autodetect repo/branch/base.
- Required inputs: нет
- Optional/schema inputs: `repo_root`, `owner`, `issue`, `branch`, `base`, `path`, `worktree_path`, `lease_sec`
- Режим: advisory
- Approval / issue requirements: Approval не требуется — координационная запись присутствия. `owner` берётся из аргумента или `$COORDCTL_OWNER`.
- Не использовать когда: cwd не внутри git-репозитория (задать `repo_root`), или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_begin","arguments":{"owner":"codex:session","path":"README.md"}}`
- Fallback/blocker: никогда не падает из-за overlap; overlap возвращается как warning на intent.

### coordctl_intent_acquire
- Когда: записать или продлить Git-aware intent на file/hunk region. Append-only: запись всегда успешна.
- Required inputs: `repo_root`, `path`, `owner`, `base`, `region_kind`, `region_id`
- Optional/schema inputs: `issue`, `lease_sec`, `session_id`
- Режим: advisory
- Approval / issue requirements: Approval не требуется — координационная запись. `issue` optional metadata.
- Не использовать когда: region не вычислен корректно, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_intent_acquire","arguments":{"repo_root":"/int/tools","path":"README.md","owner":"codex:session","base":"main","region_kind":"hunk","region_id":"12:18"}}`
- Fallback/blocker: `COORD_OVERLAP`/`STALE_BASE_OBSERVED` — warnings; запись проходит. На реальном overlap того же региона остановиться и спросить владельца, не перезаписывать.

### coordctl_status
- Когда: нужно read-only посмотреть active coordctl sessions/leases.
- Required inputs: `repo_root`
- Optional/schema inputs: `path`, `owner`, `issue`, `all`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова.
- Не использовать когда: repo target/profile не подтверждён, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_status","arguments":{"repo_root":"/int/tools"}}`
- Fallback/blocker: status — не permission gate, но часть дисциплины. Если он недоступен, зафиксировать это в closeout, не чистить и не перезаписывать чужое присутствие; при риске shared overlap остановиться и спросить владельца.

### coordctl_heartbeat
- Когда: нужно продлить active coordctl session и связанные leases.
- Required inputs: `session_id`
- Optional/schema inputs: `lease_sec`
- Режим: advisory
- Approval / issue requirements: Approval не требуется для продления своей session.
- Не использовать когда: session не принадлежит текущей задаче, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_heartbeat","arguments":{"session_id":"<session-id>"}}`
- Fallback/blocker: если heartbeat не прошёл, проверить status; не блокер.

### coordctl_release
- Когда: снять coordctl sessions/leases по `session_id`, `issue`, `lease_id`, `owner` или `path`.
- Required inputs: нет
- Optional/schema inputs: `session_id`, `repo_root`, `issue`, `lease_id`, `owner`, `path`
- Режим: advisory
- Approval / issue requirements: Approval не требуется для release своей работы. `--owner`/`--path`/`--issue` требуют `repo_root` как safety-scope.
- Не использовать когда: selector может зацепить чужую active работу без необходимости, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_release","arguments":{"repo_root":"/int/tools","lease_id":"<lease-id>"}}`
- Fallback/blocker: если selector неоднозначен, сначала вызвать `coordctl_status`.

### coordctl_cleanup
- Когда: нужно dry-run или применить обязательную уборку session: release leases, финальный статус, optional safe worktree/branch deletion.
- Required inputs: `session_id`
- Optional/schema inputs: `final_state`, `delete_worktree`, `delete_branch`, `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: `dry_run` безопасен; `apply` с удалением worktree/branch — destructive maintenance, требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Не использовать когда: session не принадлежит текущей задаче, cleanup scope не подтвержден, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_cleanup","arguments":{"session_id":"<session-id>","final_state":"released","dry_run":true}}`
- Fallback/blocker: сначала dry-run; apply только после понятного списка удаляемого.

### coordctl_gc
- Когда: нужно dry-run или очистить expired/final coordctl runtime state; это destructive maintenance.
- Required inputs: нет
- Optional/schema inputs: `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: `dry_run` безопасен; `apply` — destructive maintenance, требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Не использовать когда: есть сомнение, что active session могла быть ошибочно expired, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_gc","arguments":{"dry_run":true}}`
- Fallback/blocker: не чистить вручную SQLite/runtime files.

### coordctl_merge_dry_run
- Когда: нужно read-only проверить, сольются ли два Git refs без tracked-файловых изменений.
- Required inputs: `repo_root`, `target`, `branch`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова.
- Не использовать когда: refs не подтверждены, repo target/profile не подтверждён, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_merge_dry_run","arguments":{"repo_root":"/int/tools","target":"main","branch":"agent/INT-1/a"}}`
- Fallback/blocker: при конфликте не merge; остановиться и запросить решение.
