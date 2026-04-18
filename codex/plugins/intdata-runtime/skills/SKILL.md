---
name: intdata-runtime
description: Выполняй host, SSH, Firefox, vault sanitize и runtime GC операции через MCP-инструменты intData Runtime.
---

# intData Runtime

Используй этот skill для runtime-диагностики, host verification, SSH transport resolution, запуска dedicated Firefox MCP profiles, vault sanitize и runtime GC.

## Capability skills

- `intdata-runtime-host-diagnostics`: `host_preflight`, `host_verify`, `host_bootstrap`, `recovery_bundle`.
- `intdata-runtime-ssh`: `ssh_resolve`, `ssh_host`.
- `intdata-runtime-firefox-browser-profiles`: dedicated Firefox MCP profile launch.
- `intdata-runtime-vault-maintenance`: vault sanitize and runtime vault GC.

## Инструменты

- `host_preflight`
- `host_verify`
- `host_bootstrap`
- `recovery_bundle`
- `ssh_resolve`
- `ssh_host`
- `browser_profile_launch`
- `intdata_vault_sanitize`
- `intdata_runtime_vault_gc`

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
- Этот plugin также заменяет old plugin ID `intdata-vault`; не используй его как active install surface.
