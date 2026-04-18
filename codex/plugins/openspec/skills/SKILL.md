---
name: openspec
description: Выполняй OpenSpec list/show/validate/status и lifecycle-мутации через MCP-инструменты OpenSpec.
---

# OpenSpec

Используй этот skill для OpenSpec discovery, validation и явно утверждённых lifecycle mutations в `/int/tools` и других `/int/*` repos.

## Инструменты

- `openspec_list`: список changes или specs.
- `openspec_show`: показать change/spec.
- `openspec_status`: показать completion status.
- `openspec_validate`: validate change/spec/catalog.
- `openspec_instructions`: получить enriched instructions по artifact.
- `openspec_new`, `openspec_exec`, `openspec_spec`: mutating/structured lifecycle operations.

## Правила выполнения

- В MCP-enabled runtime этот plugin tool surface является обязательным first path для OpenSpec.
- Не вызывай `openspec` CLI или repo-local wrappers `codex/bin/openspec*` напрямую, если доступен MCP-инструмент этого плагина.
- Не используй отсутствие `openspec` в Windows `PATH` как причину для прямого вызова `codex/bin/openspec.cmd`/`.ps1`; используй MCP tool.
- Если MCP tool недоступен или возвращает blocker для нужной операции, остановись, зафиксируй tool/error и запроси owner approval на direct CLI/wrapper fallback.
- Перед planning/proposal/spec/capability-boundary задачами открой repo-local `openspec/AGENTS.md`, если он есть.
- В `EXECUTE` не создавай lifecycle "на всякий случай"; используй только active agreed change/spec.
- Mutating OpenSpec operations требуют `confirm_mutation=true`, `issue_context=INT-*` и явное owner approval.
- Для `/int/tools` любые tracked tooling/process mutations требуют active OpenSpec package; если source-of-truth не определён, остановись и зафиксируй blocker.
