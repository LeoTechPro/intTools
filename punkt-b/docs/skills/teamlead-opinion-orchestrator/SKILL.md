---
name: teamlead-opinion-orchestrator
description: "Project-specific teamlead-first orchestration for independent role opinions, green-milestone commits, and accepted finish cleanup."
---

# Teamlead Opinion Orchestrator

## When To Use
- Любая major change по matrix из `templates/swarm-risk-matrix.yaml`.
- Любой green-milestone commit.
- Любой финальный FINISH/`issue:push:done`.

## Core Rules
- Основная сессия исполняет изменения и пишет итог владельцу.
- Specialist opinions всегда независимые: отдельный `codex exec --ephemeral` на роль.
- Teamlead orchestrator обязателен в двух режимах:
  - `milestone` перед `issue:commit`
  - `finish` перед `issue:push:done`
- После зелёного milestone коммит не откладывается “на потом”.
- Если acceptance checklist зелёный, задача закрывается через `issue:push:done`, а issue-scoped `~/.codex/tmp/punkt-b` артефакты дочищаются.

## Runbook
1. Классифицируй scope через `ops/teamlead/role_opinion_matrix.py`.
2. Запусти `ops/teamlead/teamlead_orchestrator.sh --mode milestone|finish`.
3. Если orchestrator вернул `request_changes`, устрани их внутри scope и повтори.
4. Если `milestone` зелёный, делай `issue:commit`.
5. Если `finish` зелёный и acceptance checklist complete, делай `issue:push:done`.

## Do Not
- Не подменяй role-opinions внутренним reasoning основной сессии.
- Не пропускай green-milestone commit для major change.
- Не оставляй accepted issue открытой “до команды владельца”, если процессный путь уже зелёный.
