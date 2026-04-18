# Маршрутизатор intData Control

- Используй этот skill как входную точку для lockctl, OpenSpec, Multica, routing, sync-gate, publish и gate receipts.
- Перед tracked-правками в `/int/tools` бери lockctl lock на каждый файл и работай только в рамках INT-* issue.
- Mutating tools без `confirm_mutation=true`, `issue_context=INT-*` и owner approval не вызывать.

## Capability skills

- `lockctl`: lockctl: locks для tracked-правок.
- `openspec-read`: OpenSpec read-only discovery.
- `openspec-mutation`: OpenSpec lifecycle mutations.
- `multica-issue-workflow`: Multica issue workflow.
- `multica-entities-config`: Multica entities и config.
- `multica-daemon-auth-attachments`: Multica daemon, auth и attachments.
- `routing`: Routing registry validation.
- `sync-gate-publish`: Sync gate и publication.
- `gate-receipts-commit-binding`: Gate receipts и commit binding.

## Общие правила

- Сначала выбирай capability skill, затем конкретную tool-card.
- Не вызывай mutating/high-risk tools без owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Если required args неизвестны, остановись как blocker и не подменяй MCP прямым shell fallback.
