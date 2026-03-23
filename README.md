# intTools

`/int/tools` — machine-wide tooling repo `LeoTechPro/intTools` с каноническим путём `/int/tools`.

## Назначение

- reusable ops/process/tooling для контуров в `/int/*`;
- host helpers, bootstrap scripts, hooks и shared runbooks;
- versioned overlays для Codex/OpenClaw и соседних ops-систем.

## Границы ответственности

- business product-core и user-facing shells остаются в owner-репозиториях;
- runtime state и реальные секреты живут во внешних host paths;
- tooling-модуль не подменяет собой локальные owner-docs продуктовых репозиториев.

## Основные модули

- `lockctl/` — machine-local runtime writer-lock для Codex/OpenClaw;
- `gatesctl/` — machine-wide runtime для gate receipts, approvals и commit binding;
- `codex/` — versioned host-tooling, managed assets и project overlays для Codex CLI;
- `openclaw/` — versioned overlay для локального OpenClaw runtime;
- `data/` — внешний tooling/configs слой для backend-core `/int/data`;
- `probe/` — maintenance и audit-утилиты для `/int/probe`;
- `gemini-openai-proxy/` — internal-vendor copy локального OpenAI-compatible proxy для Gemini;
- `openspec/changes/` и `openspec/specs/` — proposal/spec материалы этого repo.

## Codex и OpenClaw

- runtime Codex живёт в `~/.codex`, а versioned overlay и bootstrap-утилиты — в `codex/`;
- `codex/projects/` хранит tracked project overlays для runtime `~/.codex/projects/`;
- `codex/tools/mcp-obsidian-memory/` содержит локальный MCP-сервер для vault `/2brain`;
- `codex/tools/obsidian-desktop/` хранит repo-managed launcher и desktop config для Obsidian;
- `codex/assets/codex-home/skills/javascript/` хранит repo-managed resources, scripts и templates для JavaScript skill assets;
- runtime OpenClaw живёт в `~/.openclaw`, а versioned overlay и runbooks — в `openclaw/`.

## Полезные команды

- `lockctl --help` — справка по file lease-локам;
- `gatesctl --help` — справка по gate receipts и commit binding;
- `/int/tools/codex/bin/codex-host-bootstrap` — bootstrap рабочего минимума Codex/OpenClaw/cloud tooling;
- `bash /int/tools/openclaw/ops/verify.sh` — проверка overlay OpenClaw;
- `AUTH_TYPE=oauth-personal HOST=127.0.0.1 PORT=11434 npm start` из `gemini-openai-proxy/` — локальный запуск proxy.
