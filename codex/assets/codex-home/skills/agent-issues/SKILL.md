---
name: agent-issues
description: 'Универсальный процесс работы с GitHub Issues и machine-wide lockctl:
  issues, worklog/closed, locks.'
knowledge_mode: hybrid-core-reference
last_verified_at: "2026-02-25"
refresh_interval_days: 30
official_sources:
  - https://cli.github.com/manual
  - https://docs.github.com/issues
---

# Agent Issues

## Process Core (stable)
- Работай через `gh issue`/`gh project`, без прямого редактирования локальных SQLite/lockctl state.
- Привязывай реализацию к issue + lock-flow проекта.
- Поддерживай machine-wide locks через `lockctl`, а не через project-local YAML-ledger.
- В `FINISH` выполняй только closure-процедуры по текущему scope; push — только explicit.

## Goal
Work with GitHub Issues and machine-wide `lockctl` in any repo without hardcoded paths.
- OpenSpec = источник требований/контекста; GitHub Issues = трекинг исполнения (worklog/статусы). `lockctl` stores runtime lock truth in machine-local SQLite lease-state; `paths` must reference files only, not directories. Manage locks via this skill after `gh issue create` existing issue (`gh issue view` must pass).
- Create new `<zone>-<function>.N` **только после** утверждённой OpenSpec‑спеки/дельты. Консультации без правок остаются комментариями в эпике `<zone>-<function>` без новых задач. Эпики создаются только по запросу владельца.
- Не дёргай владельца без блокеров: если задача однозначна и решаема в рамках правил, выполняй и фиксируй результат в worklog/closed; вопросы задавай только при конфликте требований, нехватке данных, или необходимости санкции на high-risk действия.

## Workflow
1. Locate project context from current cwd.
   - Find the project `AGENTS.md` and the machine-wide lock policy in `/home/leon/.codex/AGENTS.md`.
   - Detect whether the project requires issue-bound locks (for punctb: yes, `issue_id` in `lockctl` is mandatory).
   - Example command: `sed -n '1,220p' /home/leon/.codex/AGENTS.md`

2. Read project rules.
   - Open `AGENTS.md` (and `GEMINI.md` if required by the project).
   - If the request involves planning/changes, open `openspec/AGENTS.md` and the relevant change proposal/spec delta first.
   - OpenSpec reference for any repo: `openspec/AGENTS.md` (authoritative workflow and spec format).
   - Follow the project’s schema, consult IDs, and templates (including issue prefix).
   - If the project uses a fixed issue_prefix (e.g. `pb`) for hash IDs, create zonal tasks with explicit `--id <zone>-<function>.N`.
   - If AGENTS defines mandatory fields for Worklog/Closed, ensure the references/templates include them.
   - If you are a spawned agent, you MUST follow the same AGENTS rules (lockctl, GitHub Issues) and record `spawn_agent_id`/`spawn_agent_utc` in GitHub Issue comments/worklog.

3. Consult GitHub CLI docs (official).
   - Use `gh issue --help`, `gh project --help`, `gh api --help` as source of truth.
   - If the project provides a GitHub process doc URL, open it and follow it.

4. Choose issue type deliberately (ITIL/ITSM guided).
   - Use references/issue-type-selection.md.
   - Never default to `task` without justification.

5. Если задача включает миграции БД, зафиксируй в acceptance обязательный DBA‑гейт: DBA проверяет все невыполненные миграции и отсутствие конфликтов до выполнения devops-role; гейт = подтверждение DBA в GitHub Issues без дополнительных согласований (если владелец не указал иное). Дополнительно фиксируй требования: версия миграции должна записываться в таблицу миграций проекта (`schema_migrations` или эквивалент), архивные миграции не применяются.

6. Keep locks in sync via `lockctl`.
   - Add/refresh/remove machine-wide locks for existing GitHub Issues; do not store context outside `lockctl`/issue flow.
   - Store locks only on file paths (directories are forbidden).
   - Если `lockctl status` не возвращает активного lease, это значит, что lock truth отсутствует и перед commit-flow нужен новый `lockctl acquire`.
   - Если в рабочем дереве есть «неожиданные изменения», не относящиеся к текущей задаче, это не блокер: не откатывай/не stash’и/не трогай их без прямого запроса владельца. По умолчанию просто не включай их в свою задачу и зафиксируй наблюдение в GitHub Issues handoff/worklog.
   - Если использовался spawn-agent, trace metadata фиксируется в GitHub Issue comments/worklog, а не в YAML-ledger.
   - Если lease истёк, это блокирующее состояние для commit-flow: ставь новый `lockctl acquire` по своей задаче.
   - При наличии чужого активного lease на нужном файле не перехватывай его вручную; действуй по process rules проекта.
   - Never edit `lockctl` SQLite directly.

7. Use GitHub CLI (`gh issue`, `gh project`) only.
   - Create, update, comment, close via `gh issue`.
   - Do not edit SQLite directly.

8. Worklog after each meaningful step.
   - Use references/worklog-template.md.
   - Include tools used and changed files list.
   - If spawn-agent used, include `spawn_agent_id` and `spawn_agent_utc` (and `parent_session_id` if available).

9. Close only when acceptance criteria are met.
   - Use references/closed-template.md.

10. Handoff or pause.
   - Leave a worklog with next steps and risks.
   - Use references/handoff-template.md for the handoff block when applicable.

11. Session close (when ending work).
   - Use references/session-close-checklist.md.
   - Если владелец сказал «Завершайся», трактуй это как явную команду на полный цикл завершения: прогнать релевантные ревью/quality gates, обновить документацию, закрыть GitHub Issue где acceptance выполнен, отметить выполненные пункты чеклистов в OpenSpec (tasks/spec), выполнить `git add`/`git commit` только своих релевантных правок (чужие изменения не включать, не откатывать и не скрывать), использовать осмысленное сообщение коммита на русском языке, затем снять локи и очистить `.agents/tmp` (по правилам проекта). Миграции/деплой допускаются только в локальном контуре и строго по проектным гейтам (например, DBA-gate для миграций).

12. Sync instructions if required.
   - If you change `AGENTS.md`, sync `GEMINI.md` per project rules.
   - If the project uses zonal IDs, keep explicit cross-links via labels/milestones/issue comments; avoid any local JSONL sync layer for task state.
   - After `git pull --rebase`, run `gh auth status` and project/issue consistency checks (scripts/report), then continue.

## References
- OpenSpec: `openspec/AGENTS.md` (project root)
- references/ledger-rules.md
- GitHub CLI manual: https://cli.github.com/manual
- references/issue-type-selection.md
- references/worklog-template.md
- references/closed-template.md
- references/handoff-template.md
- references/session-close-checklist.md

## Volatile References (on-demand)
- GitHub CLI flags/поведение, Project API, и policy удалённых сервисов проверяй по официальным docs в момент задачи.
- Не полагайся на устаревшие локальные примеры команд, если они конфликтуют с `gh --help`.

## Freshness Gate
- Если с последней верификации прошло более `refresh_interval_days`, считай раздел `Volatile References` потенциально устаревшим.
- При малейшем сомнении в синтаксисе/поведении `gh` выполняй on-demand проверку через официальные источники.
