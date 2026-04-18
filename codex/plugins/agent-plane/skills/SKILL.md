---
name: agent-plane
description: Вызовы neutral intData Agent Tool Plane: общий tool/policy/audit слой для Agno, OpenClaw и Codex App.
---

# intData Agent Plane

Используй этот plugin, когда нужно проверить или вызвать facade-neutral tool plane.

## Tools

- `agent_plane_tools`: список tool surface neutral plane.
- `agent_plane_call`: вызов canonical tool через neutral plane.
- `agent_plane_audit_recent`: последние audit entries.

## Rules

- Не добавляй и не используй `cabinet_*` tools; Cabinet absorption находится вне текущего scope.
- Для Codex App указывай `facade=codex_app`.
- Mutating calls требуют `approval_ref`; без него neutral plane должен вернуть policy rejection.
- Секреты не передавай в `principal`, `context` или `args`.
