---
name: coordctl
description: Coordctl Git-aware coordination для параллельных agent edits. Используйте для session/intent leases, hunk-level coordination, heartbeat, release, status и merge dry-run параллельно legacy lockctl.
---

# coordctl: Git-aware coordination

- Используй эту capability-группу только для новой параллельной координации `coordctl`; legacy `lockctl` остается fallback.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.
- MCP-first routing: use `mcp__intdata_control__coordctl_*` raw tools when available; if they are not visible, run `tool_search` for `coordctl` before shell fallback.
- Shell fallback is degraded mode only, because Codex shell sandbox may not have access to runtime coordination storage.

## Tool cards

### coordctl_session_start
- Когда: нужно зарегистрировать agent/session branch перед hunk/file intent leases.
- Required inputs: `repo_root`, `owner`, `branch`, `base`
- Optional/schema inputs: `issue`, `worktree_path`, `lease_sec`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет подтвержденного repo/branch/base, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_session_start","arguments":{"repo_root":"D:/int/tools","owner":"codex:session","branch":"agent/INT-1/a","base":"main"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### coordctl_intent_acquire
- Когда: нужно взять Git-aware lease на file/hunk region перед tracked-правкой.
- Required inputs: `repo_root`, `path`, `owner`, `base`, `region_kind`, `region_id`
- Optional/schema inputs: `issue`, `lease_sec`, `session_id`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: region не вычислен, base устарел/неизвестен, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_intent_acquire","arguments":{"repo_root":"D:/int/tools","path":"README.md","owner":"codex:session","base":"main","region_kind":"hunk","region_id":"12:18"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул `COORD_CONFLICT`/`STALE_BASE`/policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### coordctl_status
- Когда: нужно read-only посмотреть active coordctl sessions/leases.
- Required inputs: `repo_root`
- Optional/schema inputs: `path`, `owner`, `issue`, `all`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: repo target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_status","arguments":{"repo_root":"D:/int/tools"}}`
- Fallback/blocker: если required args неизвестны или MCP вернул policy/config error, остановиться и записать blocker вместо shell fallback.

### coordctl_heartbeat
- Когда: нужно продлить active coordctl session и связанные leases.
- Required inputs: `session_id`
- Optional/schema inputs: `lease_sec`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: session не принадлежит текущей задаче, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_heartbeat","arguments":{"session_id":"<session-id>"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### coordctl_release
- Когда: нужно снять coordctl sessions/leases по `session_id` или `issue`.
- Required inputs: нет
- Optional/schema inputs: `session_id`, `repo_root`, `issue`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: scope release не подтвержден, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_release","arguments":{"session_id":"<session-id>"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### coordctl_cleanup
- Когда: нужно dry-run или применить обязательную уборку session: release leases, финальный статус, optional safe worktree/branch deletion.
- Required inputs: `session_id`
- Optional/schema inputs: `final_state`, `delete_worktree`, `delete_branch`, `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: session не принадлежит текущей задаче, cleanup scope не подтвержден, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_cleanup","arguments":{"session_id":"<session-id>","final_state":"released","dry_run":true}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### coordctl_gc
- Когда: нужно dry-run или очистить expired/final coordctl runtime state; это mutating maintenance.
- Required inputs: нет
- Optional/schema inputs: `dry_run`, `apply`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_gc","arguments":{"dry_run":true}}`
- Fallback/blocker: если MCP вернул policy/config error или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.

### coordctl_merge_dry_run
- Когда: нужно read-only проверить, сольются ли два Git refs без tracked-файловых изменений.
- Required inputs: `repo_root`, `target`, `branch`
- Optional/schema inputs: нет
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: refs не подтверждены, repo target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"coordctl_merge_dry_run","arguments":{"repo_root":"D:/int/tools","target":"main","branch":"agent/INT-1/a"}}`
- Fallback/blocker: если required args неизвестны или MCP вернул policy/config error, остановиться и записать blocker вместо shell fallback.
