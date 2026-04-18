---
name: intdata-runtime
description: Выполняй host, SSH и Firefox runtime-операции через MCP-инструменты intData Runtime.
---

# intData Runtime

Используй этот skill для runtime-диагностики, host verification, SSH transport resolution и запуска dedicated Firefox MCP profiles.

## Инструменты

- `host_preflight`
- `host_verify`
- `host_bootstrap`
- `recovery_bundle`
- `ssh_resolve`
- `ssh_host`
- `browser_profile_launch`

## Прямой workflow

- Preflight запускай через `host_preflight`; это read-only проверка локального runtime.
- Host verification запускай через `host_verify` с явными structured `args`.
- SSH endpoint резолви через `ssh_resolve`, не через прямой вызов resolver scripts.
- Dedicated Firefox profile запускай через `browser_profile_launch` с одним из разрешённых `profile` enum.
- Если нужного инструмента нет в текущем model context, сначала запроси его через `tool_search` по точному имени; не заменяй его shell-вызовом автоматически.

## Guardrails

- Не вызывай runtime wrappers напрямую, если есть MCP-инструмент этого плагина.
- Mutating operations требуют `confirm_mutation=true` и `issue_context=INT-*`.
- Browser profile launch является mutating/interactive operation; запускай только по задаче, где browser proof действительно нужен.
- Owner Chrome не использовать как default fallback; frontend/browser diagnostics идут через dedicated Firefox MCP runtime.
- Этот plugin заменяет старые `intdata-host`, `intdata-ssh`, `intdata-browser`; не используй удалённые tool names в новых инструкциях.
