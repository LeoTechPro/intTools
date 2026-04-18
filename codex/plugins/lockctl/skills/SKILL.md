---
name: lockctl
description: Управляй runtime lease-локами файлов через MCP-инструменты intData Locks.
---

# intData Locks

Используй этот skill перед файловыми мутациями в `/int/*`, когда repo policy требует runtime locks.

## Инструменты

- `lockctl_status`: читает active/expired locks по repo/path/owner/issue.
- `lockctl_acquire`: берёт или продлевает lease-lock на конкретный файл.
- `lockctl_release_issue`: снимает все active locks для issue в repo.
- `lockctl_gc`: удаляет expired locks из runtime storage.

## Правила lock-flow

- Не вызывай `lockctl` CLI напрямую, если доступен MCP-инструмент этого плагина.
- Лок берётся только на конкретный файл, не на директорию.
- Перед правкой укажи `repo_root`, `path`, `owner`, `reason`; для issue-disciplined задач укажи issue id.
- В текущей MCP-реализации issue может требовать numeric id; если repo policy требует `INT-*`, зафиксируй конфликт и используй numeric часть только как технический adapter constraint.
- После завершения scope сними locks через `lockctl_release_issue` или целевой release-flow, если он доступен.
- Expired lock не подменяет ownership: проверь status перед повторным acquire, если есть сомнение.
