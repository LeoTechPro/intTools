# Маршрутизатор intData Brain

- Используй этот skill как входную точку для IntBrain MCP: контекст, память, граф людей, политики, jobs и PM.
- Для записи в IntBrain требуются `confirm_mutation=true`, `issue_context=INT-*` и явное owner approval.

## Capability skills

- `context-memory`: IntBrain context и memory.
- `people-graph-policies`: IntBrain people, graph и policies.
- `jobs-runtime`: IntBrain jobs runtime.
- `pm-dashboard-tasks`: IntBrain PM dashboard и tasks.
- `session-memory`: IntBrain session memory.
- `external-imports`: IntBrain external imports.

## Общие правила

- Сначала выбирай capability skill, затем конкретную tool-card.
- Не вызывай mutating/high-risk tools без owner approval, `confirm_mutation=true` и `issue_context=INT-*`.
- Если required args неизвестны, остановись как blocker и не подменяй MCP прямым shell fallback.
