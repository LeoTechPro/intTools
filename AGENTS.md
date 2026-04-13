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

⚠️ Сначала прочитайте [корневой AGENTS.md](/int/AGENTS.md).

## Browser Runtime Inheritance
- Для сессий, стартующих из этого репозитория, default frontend-диагностика и browser-proof выполняются через dedicated Firefox DevTools MCP runtime с persistent profiles.
- Канонический policy, runtime layout и fallback-ограничения задаются только в `/int/AGENTS.md` (раздел `Frontend Browser Runtime Policy`) и наследуются без локальной переинтерпретации.
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
- runtime state и реальные секреты живут во внешних host paths, а не в repo.

## What not to mutate

- не складывать сюда canonical product domains и user-facing product shells;
- не использовать repo как permanent runtime storage;
- не подменять локальные product README/AGENTS процессными копиями в tooling repo.

## Integration expectations

- reusable tooling хранится здесь, а не в корне `/int` и не в чужих product repos;
- product repos подключают этот contour извне через scripts, hooks и documented runbooks;
- self-authored/versioned Codex tooling и wrapper-скрипты должны жить в `/int/tools/codex/**`, а не в `~/.codex` / `C:\Users\intData\.codex`;
- reusable browser tooling, Firefox MCP launcher-ы и tracked project overlays живут только в `/int/tools/codex/**`;
- runtime layout для dedicated Firefox MCP contour документируется и поддерживается только из `/int/tools/codex/**` + `/int/.runtime/firefox-mcp/**`;
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

## Docs split

- `README.md` хранит только документацию и инструкции по репозиторию.
- `AGENTS.md` хранит только process/rules/gates/commit-policy этого repo.
- `RELEASE.md` ведётся опционально: обновляется только по прямому запросу владельца или в задаче на подготовку релиз-коммуникации.

## Git и завершение работы

- Перед новой работой в этом git-репозитории агент обязан проверить чистоту дерева и upstream текущей ветки; при clean tree и валидном upstream автоматически выполняется `git pull --ff-only` без дополнительного вопроса владельцу.
- Автосинхронизация `git pull --ff-only` выполняется только на чистом дереве с корректным upstream; при любом блокере работа приостанавливается до явных инструкций владельца, в запросе владельцу нужно коротко предложить варианты дальнейших действий.
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

## Env Policy (Strict)
- В git допускаются только шаблоны `*.env.example` и `*.example`.
- Любые `*.env` и `config/runtime/*.env` запрещены в индексе.
- Runtime-секреты хранятся только вне git (локальные env/secret-store).

## Spec-First Policy
- Главный приоритет любой реализации — согласованная актуальная спека (OpenSpec / approved spec source-of-truth для контура).
- Если спеки нет, она неполная, противоречивая или не фиксирует API/contracts/capability boundaries, сначала нужно довести спеку до согласованного состояния и только потом приступать к реализации.
- Изменения API, RPC, schema contracts, payload shape, capability boundaries и access semantics без зафиксированной и согласованной спеки запрещены.
- Если реализация расходится со спекой, приоритет у спеки; сначала исправляется/уточняется spec-source-of-truth, затем код.
- Любой owner-facing triage обязан явно ответить: какая спека является source-of-truth, полна ли она и разрешает ли текущую реализацию.
