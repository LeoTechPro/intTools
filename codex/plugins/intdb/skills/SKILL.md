---
name: intdb
description: Выполняй intData DBA doctor, migration и smoke workflows через MCP-обёртку intdb.
---

# intData DBA

Используй этот skill для DB diagnostics, migration status, SQL/apply/smoke и owner-gated local Supabase workflows.

## Capability skills

- `intdb-doctor-status`: help, doctor, and read-only status checks.
- `intdb-migrations`: migration status and owner-gated migration apply.
- `intdb-sql-apply`: SQL execution, file apply, dump/restore/clone/copy.
- `intdb-local-smoke`: owner-gated disposable local Supabase smoke workflows.

## Инструмент

- `intdata_cli`: guarded MCP wrapper над intdb. В `command` передавай `intdb`; фактическую intdb-команду передавай первым элементом `args`.

Примеры формы вызова:

- help: `command="intdb"`, `args=["--help"]`
- read-only doctor: `command="intdb"`, `args=["doctor", ...]`
- migration status: `command="intdb"`, `args=["migrate", "status", ...]`

## Guardrails

- Не вызывай `intdb.py`, `intdb.ps1`, `intdb.cmd` или shell wrappers напрямую, если доступен `intdata_cli`.
- Read-only/help/status допустимы без mutation confirmation.
- SQL execution, file apply, dump/restore/clone/copy, migration apply и local-test считаются mutating/high-risk: нужны `confirm_mutation=true`, `issue_context=INT-*` и явное owner approval.
- Не подставляй DB profile, host, env или credentials по догадке. Если profile/secret отсутствует, остановись и зафиксируй blocker.
- Для `/int/data` DB changes должны соответствовать approved OpenSpec/source-of-truth перед apply.
