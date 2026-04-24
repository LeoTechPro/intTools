---
name: dba
description: Internal int-tools skill entrypoint for the dba plugin. Use as the router for dba doctor/status, read-only SQL smoke, migrations, and controlled SQL apply workflows.
---

# Маршрутизатор intDBA

- Используй этот skill для DB doctor/status, migration review, SQL/apply planning и disposable local smoke.
- `intdata_cli` является command-router: сначала выбери безопасный subcommand, затем проверь approval requirements.
- Production SQL/apply/dump/restore без отдельной owner-команды запрещены.

## Capability skills

- `doctor-status`: intDBA doctor/status.
- `migrations`: intDBA migrations.
- `sql-apply`: intDBA SQL/apply.
- `local-smoke`: intDBA local smoke.

## Общие правила

- Сначала выбирай capability skill, затем конкретную tool-card.
- Не вызывай mutating/high-risk tools без owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Если required args неизвестны, остановись как blocker и не подменяй MCP прямым shell fallback.
