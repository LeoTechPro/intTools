---
name: multica
description: Веди agent task-control-plane через MCP-обёртку Multica Issues.
---

# Multica

Используй этот skill для agent coordination через Multica Issues. GitHub Issues, `gh issue` и `gh project` не являются fallback для agent task state.

## Инструмент

- `multica_issue`: structured wrapper над `multica issue <command>`.

## Основной workflow

- Перед нетривиальной работой найди или проверь текущий `INT-*` через `multica_issue`.
- Для чтения используй `list`, `get`, `search`, `runs`, `run-messages`.
- Для изменения issue используй `create`, `update`, `assign`, `status`, `comment` только с `confirm_mutation=true`, если wrapper требует confirmation.
- Комментарии/worklog/close-out фиксируй в Multica issue, а не в GitHub Issues.

## Guardrails

- В MCP-enabled runtime этот plugin tool surface является обязательным first path для Multica issue state.
- Не вызывай `multica` CLI напрямую, если доступен MCP-инструмент этого плагина; это относится к `create`, `comment`, `status`, `update`, `assign`, `get`, `list` и `search`.
- Для mutating commands указывай `issue_context=INT-*`, когда задача уже привязана к issue.
- Если MCP tool недоступен или возвращает blocker для нужной операции, остановись, зафиксируй tool/error и запроси owner approval на direct CLI fallback.
- Если Multica недоступна или issue не найден, остановись и сообщи blocker; не переходи на GitHub Issues.
- Не создавай новую issue без прямого запроса владельца или утверждённого process path.
