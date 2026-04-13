# Firefox DevTools MCP Default Runtime

## Назначение

Этот runbook фиксирует canonical browser-proof runtime для `/int/*`: dedicated `firefox-devtools-mcp@0.9.1` с persistent profile и repo-managed launcher-ами из `/int/tools/codex/bin/**`.

## Prerequisites

- `node` и `npx` доступны в `PATH`;
- установлен Firefox 100+;
- project overlay синхронизирован в runtime через `/int/tools/codex/sync_runtime_from_repo.sh`;
- browser-proof не использует owner browser profile как default-path.

## Runtime layout

- profiles: `/int/.runtime/firefox-mcp/profiles/<profile>/`
- logs: `/int/.runtime/firefox-mcp/logs/<profile>/`
- run meta: `/int/.runtime/firefox-mcp/run/<profile>.json`

## Wrapper contract

- generic launcher: `D:/int/tools/codex/bin/mcp-firefox-devtools.ps1`
- thin entrypoint for MCP client: `D:/int/tools/codex/bin/mcp-firefox-devtools.cmd`
- profile wrappers задают только controlled inputs: `ProfileKey`, `StartUrl`, `Viewport`, `Visible`
- default mode: headless
- persistent state живёт только в profile directory

## Как запускать

- generic dry-run:
  - `pwsh -File D:/int/tools/codex/bin/mcp-firefox-devtools.ps1 -ProfileKey firefox-default -StartUrl http://127.0.0.1:8080/ -DryRun`
- generic MCP entry:
  - `D:/int/tools/codex/bin/mcp-firefox-default.cmd`
- project overlays:
  - `/int/tools/codex/projects/int/.mcp.json`
  - `/int/tools/codex/projects/assess/.mcp.json`

## Логи и диагностика

- stderr launcher-а и upstream MCP сервера пишутся в `/int/.runtime/firefox-mcp/logs/<profile>/stderr.log`
- активный launcher отмечается файлом `/int/.runtime/firefox-mcp/run/<profile>.json`
- повторный запуск того же profile-key поверх живого launcher-а запрещён

## Reset одного profile

1. Убедиться, что run-meta для profile отсутствует.
2. При необходимости закрыть активный MCP session.
3. Удалить только `/int/.runtime/firefox-mcp/profiles/<profile>/`.
4. Не трогать соседние role-профили и общие логи.

## Fallback в owner Chrome

Owner Chrome допустим только если Firefox runtime:

- не стартует;
- не покрывает нужный debug-case;
- или профиль повреждён и нужен срочный unblock.

В handoff обязательно фиксируются причина fallback и Firefox-артефакты, которых не хватило.
