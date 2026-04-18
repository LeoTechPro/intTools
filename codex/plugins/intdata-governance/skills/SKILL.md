---
name: intdata-governance
description: Выполняй governance, routing, sync-gate, publish и gate-операции через MCP-инструменты intData Governance.
---

# intData Governance

Используй этот skill для high-risk governance операций в `/int/*`: routing registry, sync gate, canonical publish, gate receipts и commit bindings.

## Инструменты

- `routing_validate`
- `routing_resolve`
- `sync_gate`
- `publish`
- `gate_status`
- `gate_receipt`
- `commit_binding`

## Прямой workflow

- Routing registry проверяй через `routing_validate`; конкретный intent резолви через `routing_resolve`.
- Git sync gate запускай через `sync_gate`, а не через `python .../int_git_sync_gate.py`.
- Публикации и deploy выполняй через `publish`, а не через raw `git push` или shell-wrapper.
- Gate status/receipt читай через `gate_status` и `gate_receipt`.
- Commit binding делай через `commit_binding` только после успешного локального commit и с текущим `INT-*`.

## Guardrails

- Не вызывай старые CLI/plugin aliases напрямую, если есть MCP-инструмент этого плагина.
- Mutating operations требуют `confirm_mutation=true` и `issue_context=INT-*`.
- `sync_gate stage=start` должен пройти до tracked file mutations, если repo policy требует sync-gate.
- `sync_gate stage=finish` с push является mutating/publication step и требует явного owner approval или прямой команды.
- Используй только структурированные args/enums инструмента; не добавляй произвольный shell passthrough.
- Этот plugin заменяет старые `intdata-routing`, `intdata-delivery`, `gatesctl`; не используй удалённые tool names в новых инструкциях.
