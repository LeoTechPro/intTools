<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## /int Agent Execution Contract

These repo-local rules include the former machine-wide `/int` rules. `D:\int` is a directory of separate repositories, not a monorepo or project root.

### Scope and Mode
- Before any task, identify the exact scope, repository, mode (`EXECUTE`, `PLAN`, `SPEC-MUTATION`, `FINISH`) and domain.
- Allowed paths are `/int/*` by default; owner tasks may also use `/home/leon/*`. Anything else requires written owner approval.
- Run `whoami` before starting work and record assumptions as `[ASSUMPTION]` when they affect execution.
- Stop and escalate if scope, access, owner, lock state, git state, or required spec is unclear.

### Rule Priority
1. Owner directives
2. Access and security
3. Execution contract
4. Spec-first policy
5. Git, lock, and process gates
6. Coding rules
7. Repo-local rules below

When rules conflict, follow the higher-priority rule and record the conflict in handoff.

### Spec-First Policy
- API, schema, contract, auth/RBAC, runtime interface, and cross-repo boundary changes require an existing approved spec before code changes.
- In `EXECUTE`, specs may be read but not rewritten. `SPEC-MUTATION` may write specs only with owner approval.
- If code and spec disagree, fix or approve the spec path first; do not silently invent contract behavior.

### Git, Multica, and Lock Gates
- Multica Issues are the only task-control-plane for agent work. GitHub Issues, `gh issue`, and `gh project` are not fallback coordination systems.
- Before non-trivial implementation, commit, push, deploy, or publication, verify a reachable Multica issue in `INT-*` format.
- Every local commit for agent work must include the current `INT-*` id in subject or body.
- Push, deploy, and publication require explicit owner approval or a direct `push/publish` command.
- Before file mutation, acquire a runtime `lockctl` lock for each changed file. Release locks after completion.
- The source of truth for locks is runtime `lockctl`, not YAML notes.
- Work only from a clean tree unless the owner explicitly scopes around existing unrelated changes; never revert or stage unrelated user changes.

### Coding and Change Discipline
- Make minimal, targeted edits; preserve existing architecture, conventions, and file structure.
- Do not add speculative flexibility, broad rewrites, or unrelated cleanup.
- Reproduce or inspect before fixing; verify the requested result before finishing.
- Do not change production state, delete data, reset history, or run destructive operations without explicit owner approval.

### Process, Paths, and Runtime
- Process gate order: Intake, Architecture, Implementation, Merge, QA, InfoSec, DevOps, Promotion.
- Do not place junk in `/int`; temporary files belong under `/int/.tmp/<ISO8601>/`.
- Reusable tooling belongs under `/int/tools/**`.
- Canonical hosts: prod `vds.punkt-b.pro`, dev `vds.intdata.pro`.
- Canonical users: `intdata` primary, `codex` runtime agent, `leon` manual-only.
- Supabase system roles and system tables must not be changed.
- Frontend diagnostics default to headless Firefox MCP with separate profiles; owner Chrome is only a documented fallback.
- If a repo-local or tooling machine-readable policy file exists, read it. If a referenced machine policy file is missing, record that as a blocker or assumption instead of treating it as available.
- Communication language is Russian unless the owner explicitly asks otherwise; record decisions, blockers, verification, and remaining risks.

## Frontend Runtime Policy
- Для сессий, стартующих из этого репозитория, default frontend-диагностика и browser-proof выполняются через dedicated Firefox DevTools MCP runtime с persistent profiles.
- Attach к owner Chrome допустим только как documented fallback по blocker-case с явной фиксацией причины в handoff.
# AGENTS — intTools

## Allowed scope

- `ops-tooling` contour для machine-wide automation;
- machine-wide ops/process/tooling, hooks, bootstrap scripts и shared runbooks;
- machine-wide delivery/publish automation для top-level repo contours `/int/*`;
- внешние tooling contours для `intdata`, `crm`, `probe`, `codex` и соседних repos;
- repo-level docs по reusable tooling и host helpers.

## Source-of-truth ownership

- `/int/tools` остаётся `ops-tooling` repo и владеет только reusable ops/process/tooling contour;
- business product-core и domain ownership остаются в соответствующих product repos;
- runtime state и реальные секреты живут вне tracked git; для intTools canonical ignored host path — `/int/tools/.runtime/**`.

## What not to mutate

- не складывать сюда canonical product domains и user-facing product shells;
- не использовать tracked repo как permanent runtime storage; ignored `/int/tools/.runtime/**` является локальным host-runtime исключением;
- не подменять локальные product README/AGENTS процессными копиями в tooling repo.

## Integration expectations

- reusable tooling хранится здесь, а не в корне `/int` и не в чужих product repos;
- product repos подключают этот contour извне через scripts, hooks и documented runbooks;
- self-authored/versioned Codex tooling и wrapper-скрипты должны жить в `/int/tools/codex/**`, а не в `~/.codex` / `C:\Users\intData\.codex`;
- reusable browser tooling, Firefox MCP launcher-ы и tracked project overlays живут только в `/int/tools/codex/**`;
- runtime layout для dedicated Firefox MCP contour документируется и поддерживается только из `/int/tools/codex/**` + `/int/tools/.runtime/firefox-mcp/**`;
- repo остаётся machine-wide tooling layer, а не отдельным business runtime.
- прямые кодовые импорты между `/int/tools` и другими top-level root-контурами `/int/*` запрещены; интеграция допустима только через documented scripts/hooks/CLI entrypoints, public APIs/contracts, events или иные явно согласованные boundary contracts.

## Escalation triggers

- попытка превратить `/int/tools` в owner business product-core;
- перенос mutable runtime-state или секретов в tracked repo;
- дублирование локальных product-docs вместо ссылок на реальные owner repos.

## Lock discipline

- Любые файловые правки в `/int/tools` запрещены без предварительного `lockctl acquire` по конкретному файлу.
- Источник истины по активным локам — только `lockctl`; project-local заметки не подменяют runtime truth.
- После завершения правки лок обязательно снимается через `lockctl release-path` или `lockctl release-issue`.

## Multica issue and commit gate
- Multica Issues are the mandatory task-control-plane for agent work in this repo; GitHub Issues, `gh issue`, and `gh project` are not used for agent task coordination and are not fallback.
- Before non-trivial implementation, commit, push, deploy, or publication, the agent must identify a reachable Multica issue id in `INT-*` format for the current task.
- Missing Multica issue id, inaccessible Multica, or an issue id that cannot be verified is a blocker: stop, report the blocker to the owner, and continue without Multica only after explicit owner approval for that exception.
- Every local commit message must contain the current Multica task id in `INT-*` format in the subject or body. A commit without `INT-*` is forbidden.
- Push/publication/deploy is forbidden if any commit being published for the current scope lacks a Multica `INT-*` id; fix the commit metadata through the safest owner-approved path before publication.
- Agent locks and close-out notes must reference the Multica `INT-*` id; generic issue ids without the Multica prefix are not sufficient for agent work.
## Docs split

- `README.md` хранит только документацию и инструкции по репозиторию.
- `AGENTS.md` хранит только process/rules/gates/commit-policy этого repo.
- `RELEASE.md` ведётся опционально: обновляется только по прямому запросу владельца или в задаче на подготовку релиз-коммуникации.

## Tooling Mutation Governance

- Любая tracked-мутация repo-owned tooling в `/int/tools/**` обязана начинаться с согласованного OpenSpec package в `openspec/changes/<change-id>/`.
- До первой tracked-правки должны существовать как минимум `proposal.md`, `tasks.md` и релевантный `spec.md` delta в `openspec/changes/<change-id>/specs/**`; `design.md` обязателен, если change меняет resolver/runtime architecture, capability boundaries или enforcement model.
- Execution допускается только против active agreed change; если `change-id`, spec source-of-truth или acceptance scope не определены, работа останавливается и эскалируется владельцу.
- Это требование распространяется на wrapper-скрипты, publish/deploy flows, hooks/gates, MCP launcher-ы, Codex/OpenClaw overlays, prompts/rules/skills, repo policy docs и любой другой tracked tooling/process asset, который меняет поведение или governance контура `/int/tools`.
- Host-local git maintenance (`.git/**`), runtime state вне git, lock receipts и untracked temp-артефакты не считаются repo-owned tooling mutations и не образуют самостоятельный OpenSpec scope.

## High-Risk Routing V1

- Machine-readable registry для repo-owned high-risk capabilities: `codex/config/agent-tool-routing.v1.json`.
- Канонический resolver/validator CLI: `codex/bin/agent_tool_routing.py`.
- Contract V1: `logical intent -> canonical engine -> thin adapter`.
- Blocked path обязателен при `missing engine`, `missing adapter`, `unsupported platform`, `adapter drift`, `unknown intent` и `ambiguous intent`.
- Verified skills для high-risk capabilities не могут подменять blocked repo-owned path автоматически; они допустимы только как explicit approved fallback metadata.
- Актуальный deduplicated MCP surface:
  - plugin `intdata-governance` заменяет `intdata-routing`, `intdata-delivery`, `gatesctl`;
  - plugin `intdata-runtime` заменяет `intdata-host`, `intdata-ssh`, `intdata-browser`.
- Публичные tool names (без alias-совместимости):
  - governance: `routing_validate`, `routing_resolve`, `sync_gate`, `publish`, `gate_status`, `gate_receipt`, `commit_binding`;
  - runtime: `host_preflight`, `host_verify`, `host_bootstrap`, `recovery_bundle`, `ssh_resolve`, `ssh_host`, `browser_profile_launch`.
- Старые plugin IDs/tool names из удалённых шести плагинов не использовать в AGENTS/skills/runbooks.
- Canonical engine roots:
  - publish/deploy family: `delivery/bin`
  - SSH / Firefox / host launchers: `codex/bin`
  - sync gate: `scripts/codex/int_git_sync_gate.py`
  - lockctl CLI/MCP: `lockctl/lockctl_core.py`, `codex/bin/mcp-intdata-cli.py --profile lockctl`
  - intdb: `intdb/lib/intdb.py`

## Git и завершение работы

- Для любой задачи с файловыми мутациями в `/int/*` обязателен двухфазный sync-gate:
  - `start`: `python /int/tools/scripts/codex/int_git_sync_gate.py --stage start` (Linux) или `python D:/int/tools/scripts/codex/int_git_sync_gate.py --stage start` (Windows) до первой правки; по умолчанию gate работает только с текущим checkout.
  - `finish`: `python /int/tools/scripts/codex/int_git_sync_gate.py --stage finish --push` (Linux) или `python D:/int/tools/scripts/codex/int_git_sync_gate.py --stage finish --push` (Windows) перед закрытием задачи; gate делает `fetch -> verify -> push -> post-push fetch`, но не делает auto-merge/rebase.
- Запрещено начинать правки без успешного `start` и запрещено завершать задачу с локальными commit-ами `ahead>0`.
- Для старого массового scan всех top-level repo требуется явный `--all-repos`; `--root-path` без `--all-repos` не используется.
- Автосинхронизация `git pull --ff-only` выполняется только на clean tree с корректным upstream и только на `start`; при любом блокере работа приостанавливается до явных инструкций владельца, в запросе владельцу нужно коротко предложить варианты дальнейших действий.
- Любая завершённая правка в `/int/tools` считается незавершённой, пока в пределах текущей задачи не создан как минимум один локальный commit в этом repo.
- Перед каждым локальным commit обязательно добавить в индекс новые файлы текущего scope и повторно выполнить `git add` для уже staged путей после каждой дополнительной правки; commit по устаревшему состоянию индекса запрещён.
- Перед каждым локальным commit обновление `RELEASE.md` не требуется; по умолчанию source-of-truth изменений — git history (commit subjects/body + diff).
- Релизный пост формируется по запросу из git-истории (commit subjects/body + diff) с ручной редактурой под целевую аудиторию.
- Если в задаче явно нужен релизлог, используем только корневой `RELEASE.md`; исторический `docs/`-путь и другие альтернативные варианты не используем.
- Перед локальным commit агент обязан проверить, не устарел ли корневой `README.md`; если правка меняет описанные там команды, структуру, маршруты, интеграции или инструкции, обновление `README.md` входит в тот же commit.
- Любой push в удалённую ветку `main` допустим только при `ALLOW_MAIN_PUSH=1` и только из локальной `main`.
- Для `/int/tools` owner-approved git-задача после локального commit и при clean tree должна завершаться немедленной canonical publication в `origin/main`; локальный commit без этой публикации считается промежуточным состоянием, если владелец явно не остановил задачу до push.
- Если canonical publication в `origin/main` завершилась non-zero, задача считается незавершённой до устранения причины и повторного успешного publish.
- Для каждого checkout/worktree обязателен локальный bootstrap `git config core.hooksPath .githooks`; tracked `.githooks/pre-push` включает этот guardrail только после такой настройки и не ограничивает push в `dev` или другие non-main branches.
- `git push` и прочие remote-операции остаются отдельным шагом и не выполняются автоматически без owner approval или явного требования локального процесса.
- Локальный `git add`/`git commit` по умолчанию остаётся дисциплиной согласованного scope: агент коммитит свои/согласованные правки, если владелец явно не указал включить больше.
- Если владелец явно командует `push/publish/выкатывай/публикуй`, агент обязан либо выполнить canonical publication по уже подготовленному publication-state, либо остановиться и спросить, что делать дальше при блокере/неоднозначности.
- При explicit owner-команде на publication запрещено по собственной инициативе дофильтровывать уже подготовленное publication-state: stash'ить, откатывать, скрывать или откладывать чужие/неатрибутированные изменения перед push/deploy.

## Env Policy (Strict)
- В git допускаются только шаблоны `*.env.example` и `*.example`.
- Любые `*.env` и `config/runtime/*.env` запрещены в индексе.
- Runtime-секреты хранятся только вне git (локальные env/secret-store).

## Режимы
- `EXECUTE`: реализация в пределах текущего approved scope без lifecycle-мутаций.
- `PLAN`: планирование без изменения lifecycle и без мутации спецификаций.
- `SPEC-MUTATION`: создание/изменение proposal/spec lifecycle только если задача реально меняет contracts/API/schema/capability boundaries.
- `FINISH`: closing pipeline по локальному diff, checks и handoff без расширения scope.

## Режимные границы
- `EXECUTE`: не открывать lifecycle/spec "на всякий случай"; любые мутации `openspec/**` запрещены без явного owner approval.
- `PLAN`: читать только summary/headers и локальный контекст; любые мутации `openspec/**` запрещены без явного owner approval.
- `SPEC-MUTATION`: применять lifecycle только если задача реально меняет contracts/API/schema/capability boundaries; любая мутация `openspec/**` допускается только по явному owner approval, без самостоятельного "додумывания" несогласованных spec-деталей.
- `FINISH`: опираться только на локальный diff, результаты checks и состояние рабочей зоны; любые мутации `openspec/**` запрещены без явного owner approval.

## Spec-First Policy
- Главный приоритет любой реализации — согласованная актуальная спека (OpenSpec / approved spec source-of-truth для контура).
- Для `/int/tools` OpenSpec обязателен не только для API/schema/capability work, но и для любых tracked tooling/process mutations: без active agreed `openspec/changes/<change-id>/` реализация запрещена.
- Если спеки нет, она неполная, противоречивая или не фиксирует API/contracts/capability boundaries, сначала нужно довести спеку до согласованного состояния и только потом приступать к реализации.
- Изменения API, RPC, schema contracts, payload shape, capability boundaries и access semantics без зафиксированной и согласованной спеки запрещены.
- Если реализация расходится со спекой, приоритет у спеки; сначала исправляется/уточняется spec-source-of-truth, затем код.
- Любой owner-facing triage обязан явно ответить: какая спека является source-of-truth, полна ли она и разрешает ли текущую реализацию.
