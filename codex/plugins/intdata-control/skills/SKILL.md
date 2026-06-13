---
name: intdata-control
description: Internal intData skill entrypoint for the intdata-control plugin. Use as the router for OpenSpec, routing, and review workflows.
---

# Маршрутизатор intData Control

- Используй этот skill как входную точку для OpenSpec и routing.
- Для Multica используй официальный `multica` CLI или официальный Multica MCP plugin, если он установлен; `intdata-control` Multica tools removed/forbidden.
- Local delivery publish wrappers removed/forbidden: do not use `/int/tools/delivery/bin/publish_*`, `/int/tools/codex/bin/publish_*.ps1`, or an `intdata-control` `publish` tool.
- Local sync-gate wrappers removed/forbidden: use explicit native git commands and repo hooks instead of `int_git_sync_gate` or `sync_gate_*` tools.
- Перед tracked-правками в `/int/tools` используй внешний probe-owned CLI `coordctl` для session/intent lease, если он доступен в PATH.
- Mutating tools без `confirm_mutation=true`, `issue_context=INT-*` и owner approval не вызывать.

## Capability skills

- `openspec-read`: OpenSpec read-only discovery.
- `openspec-mutation`: OpenSpec lifecycle mutations.
- `routing`: Routing registry validation.
- `review-find`: hostile-аудит предыдущего результата агента по реальному текущему состоянию.
- `review-fix`: перепроверка внешних findings и исправление только подтверждённых пунктов.

## Общие правила

- Сначала выбирай capability skill, затем конкретную tool-card.
- Не вызывай mutating/high-risk tools без owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Если required args неизвестны, остановись как blocker и не подменяй MCP прямым shell fallback.
- Active coordination runtime — внешний probe-owned CLI `coordctl`; intdata-control больше не экспортирует coordctl MCP tools.
