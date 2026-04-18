# Маршрутизатор intData Runtime

- Используй этот skill для host diagnostics, SSH route checks, dedicated Firefox MCP profiles и vault maintenance.
- Runtime/interactive/destructive действия требуют явного owner approval и issue context.
- По умолчанию начинай с read-only diagnostics и dry-run.

## Capability skills

- `host-diagnostics`: Runtime host diagnostics.
- `ssh`: Runtime SSH routes.
- `firefox-browser-profiles`: Firefox MCP profiles.
- `vault-maintenance`: Runtime vault maintenance.

## Общие правила

- Сначала выбирай capability skill, затем конкретную tool-card.
- Не вызывай mutating/high-risk tools без owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Если required args неизвестны, остановись как blocker и не подменяй MCP прямым shell fallback.
