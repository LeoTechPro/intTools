---
name: intdb
description: Internal int-tools skill entrypoint for the intdb plugin. Use as the router for intDB doctor/status, read-only SQL smoke, migrations, and controlled SQL apply workflows.
---

# Маршрутизатор intData DBA

- Используй этот skill для DB doctor/status, migration review, SQL/apply planning и disposable local smoke.
- `intdata_cli` является command-router: сначала выбери безопасный subcommand, затем проверь approval requirements.
- Production SQL/apply/dump/restore без отдельной owner-команды запрещены.

## Capability skills

- `doctor-status`: intDB doctor/status.
- `migrations`: intDB migrations.
- `sql-apply`: intDB SQL/apply.
- `local-smoke`: intDB local smoke.

## Общие правила

- Сначала выбирай capability skill, затем конкретную tool-card.
- Не вызывай mutating/high-risk tools без owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Если required args неизвестны, остановись как blocker и не подменяй MCP прямым shell fallback.
