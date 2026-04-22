---
name: agent-issues
description: 'Multica-first процесс работы с задачами агентов: Multica Issues, worklog/closed, runtime lockctl, commit gates и status movement.'
knowledge_mode: hybrid-core-reference
last_verified_at: "2026-04-18"
refresh_interval_days: 30
official_sources:
  - https://multica.intdata.pro
---

# Agent Issues

## Process Core (stable)
- Работай через Multica Issues как единственный task-control-plane для агентских задач.
- Используй официальный документированный `multica` CLI для issue reads/writes; если в runtime установлен официальный Multica MCP plugin (`mcp__multica__`), можно использовать его. Не используй `intdata-control` как Multica-прослойку.
- Если Multica недоступна, задача считается заблокированной: остановись, сообщи владельцу конкретный blocker и продолжай без Multica только после явного разрешения владельца.
- Привязывай реализацию к Multica issue + lock-flow проекта, если lock-flow существует.
- Поддерживай lock state через runtime `lockctl`; если доступен MCP plugin `lockctl`, используй его вместо direct CLI.
- В `FINISH` выполняй closure-процедуры по текущему Multica issue; push/PR/remote ops — только explicit.

## Goal
Work with Multica Issues and project lock-flow in any repo without hardcoded paths.
- OpenSpec = источник требований/контекста; Multica Issues = трекинг исполнения, worklog, статусы и история runs.
- В MCP-enabled runtime используй project-approved OpenSpec MCP tools для OpenSpec list/show/status/validate/lifecycle операций; direct `openspec` или repo-local `codex/bin/openspec*` wrappers не являются PATH fallback.
- Use issue-linked locks only when the project/task requires issue discipline; `lockctl.issue` is optional metadata and locks may be taken without an `INT-*` issue for non-project or pre-intake work.
- Создавай новые задачи только после утверждённой OpenSpec-спеки/дельты или прямого запроса владельца. Консультации без правок остаются комментариями в текущем Multica issue.
- Не дёргай владельца без блокеров: если задача однозначна и решаема в рамках правил, выполняй и фиксируй результат в Multica issue; вопросы задавай только при конфликте требований, нехватке данных, необходимости санкции на high-risk действия или недоступности Multica.

## Required Multica Availability Gate
1. Before starting non-trivial work, identify the current Multica issue.
   - If the task came from Multica, use that issue.
   - If there is no issue, create/import one in Multica before implementation only when the owner or project process permits it.
   - For imported/backlog work that must not auto-run, create it without agent assignee or in `backlog`.
2. Verify Multica access with the cheapest available official check:
   - `multica issue list`, `multica issue get <INT-*>`, or `multica issue search <query>`.
   - If an official Multica MCP plugin is installed, its equivalent read-only check is acceptable.
3. If Multica is unavailable:
   - Do not continue execution as an untracked task unless the owner explicitly approves that exception.
   - Report: attempted plugin tool/API, error, affected task, and safest next step.

## Required Multica Commit Gate
- Every local commit for agent work must include the current Multica task id in `INT-*` format in the commit subject or body.
- Absence of a reachable Multica issue id is a blocker for `git commit`, push, deploy, publication, PR creation, and any close-out flow that publishes code.
- If a commit in the current publication scope lacks `INT-*`, stop and report the blocker; fix commit metadata only through the safest project-approved path and owner approval where required.

## Workflow
1. Locate project context from current cwd.
   - Find canonical lock path for current project, `AGENTS.md`, and `openspec/AGENTS.md` when present.
   - If multiple lock candidates exist, pick nearest project-canonical path or ask.
   - Example command: `rg --files -g AGENTS.md -g SKILL.md`.

2. Read project rules.
   - Open `AGENTS.md` (and `GEMINI.md` if required by the project).
   - If the request involves planning/changes, open `openspec/AGENTS.md` and the relevant change proposal/spec delta first.
   - OpenSpec reference for any repo: `openspec/AGENTS.md` when present.
   - In MCP-enabled runtimes, use project-approved OpenSpec MCP tools for OpenSpec discovery/validation/lifecycle.
   - Follow the project’s schema, consult IDs, templates and issue prefix.
   - If AGENTS defines mandatory fields for Worklog/Closed, ensure the references/templates include them.
   - If you are a spawned agent, follow the same Multica issue rules and record `spawn_agent_id`/`spawn_agent_utc` in Multica comments/worklog.

3. Use Multica CLI/API/UI as source of task truth.
   - Prefer official `multica issue ...` commands for `list`, `get`, `search`, `runs`, `run-messages`, `create`, `update`, `assign`, `status`, and `comment`.
   - If CLI syntax or behavior is uncertain, inspect `multica --help`, `multica issue --help`, or the Multica API before mutating.
   - Treat ambiguous assignee/name matching as a blocker or use exact IDs.

4. Choose issue type/status deliberately.
   - Use `references/issue-type-selection.md`.
   - Never default to `task` without justification when the project has typed issue metadata.

5. Если задача включает миграции БД, зафиксируй в acceptance обязательный backend-gate: `backend-role` должен пройти внутренний цикл review/apply/smoke до green и зафиксировать это в Multica issue без дополнительных согласований (если владелец не указал иное). Дополнительно фиксируй требования: версия миграции должна записываться в таблицу миграций проекта (`schema_migrations` или эквивалент), архивные миграции не применяются.

6. Keep locks in sync.
   - Add/refresh/remove locks through runtime `lockctl`; attach `issue=INT-*` only when the task has or requires a Multica issue.
   - Store locks only on file paths; directories are forbidden.
   - Если в рабочем дереве есть неожиданные изменения, не откатывай/не stash'и/не трогай их без прямого запроса владельца. Зафиксируй наблюдение в Multica issue handoff/worklog.
   - Если использовался spawn-agent, допустимы только `spawn_agent_id`, `spawn_agent_utc`, `parent_session_id` in the project-approved lock ledger when one exists; progress stays in Multica.
   - Если лок исчез или TTL истёк, ставь новый лок по текущему Multica issue и не вмешивайся в чужие.
   - Never edit lock runtime storage directly.

7. Use Multica for task updates.
   - Create, update, comment, assign, move status and close through Multica CLI/API/UI.

8. Worklog after each meaningful step.
   - Use `references/worklog-template.md`.
   - Include tools used and changed files list.
   - If spawn-agent used, include `spawn_agent_id` and `spawn_agent_utc` (and `parent_session_id` if available).
   - If any wrapper fallback was used, include attempted official command/API, error/blocker, owner approval, and exact fallback command.

9. Close only when acceptance criteria are met.
   - Use `references/closed-template.md`.
   - Move the Multica issue to `done`/`in_review`/`blocked` according to project policy.

10. Handoff or pause.
   - Leave a Multica worklog/comment with next steps and risks.
   - Use `references/handoff-template.md` for the handoff block when applicable.

11. Session close.
   - Use `references/session-close-checklist.md`.
   - Если владелец сказал «Завершайся», трактуй это как явную команду на полный цикл завершения: прогнать релевантные ревью/quality gates, обновить документацию, закрыть/перевести Multica issue где acceptance выполнен, отметить выполненные пункты чеклистов в OpenSpec, выполнить `git add`/`git commit` только своих релевантных правок при явном запросе/проектном правиле, затем снять локи и очистить `.agents/tmp` по правилам проекта.

12. Sync instructions if required.
   - If you change `AGENTS.md`, sync `GEMINI.md` per project rules. Do this only when the user explicitly permits editing those files.
   - If the project uses zonal IDs, keep explicit cross-links in Multica issue comments/fields; avoid local JSONL sync layers for task state.

## References
- references/ledger-rules.md
- references/issue-type-selection.md
- references/worklog-template.md
- references/closed-template.md
- references/handoff-template.md
- references/session-close-checklist.md

## Volatile References (on-demand)
- Multica CLI/API behavior is live system behavior. Prefer MCP plugin tools; if plugin coverage is blocked and owner approves fallback, verify CLI syntax with `multica --help` / `multica issue --help` or the deployed API before acting.

## Freshness Gate
- Если с последней верификации прошло более `refresh_interval_days`, считай CLI/API syntax and plugin behavior potentially stale and verify before mutations.
