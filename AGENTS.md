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

Эти repo-local правила включают прежние machine-wide правила `/int`. `D:\int` — каталог отдельных репозиториев, а не монорепозиторий и не корень проекта.

### Область и режим
- Перед любой задачей определить точную область, репозиторий, режим (`EXECUTE`, `PLAN`, `SPEC-MUTATION`, `FINISH`) и домен.
- По умолчанию разрешены пути `/int/*`; owner-задачи также могут использовать `/home/leon/*`. Всё остальное требует письменного approval владельца.
- Перед началом работы выполнить `whoami`; предположения, влияющие на исполнение, фиксировать как `[ASSUMPTION]`.
- Остановиться и эскалировать, если неясны область, доступ, владелец, состояние локов, git state или обязательная спека.

### Приоритет правил
1. Директивы владельца
2. Доступ и безопасность
3. Контракт выполнения
4. Spec-first policy
5. Git, lock и process gates
6. Правила кодирования
7. Repo-local правила ниже

При конфликте правил следовать более приоритетному правилу и зафиксировать конфликт в handoff.

### Spec-first policy
- Изменения API, schema, contract, auth/RBAC, runtime interface и cross-repo boundaries требуют существующей approved spec до правок кода.
- В `EXECUTE` спеки можно читать, но нельзя переписывать. `SPEC-MUTATION` может менять спеки только с разрешения владельца.
- Если код и спека расходятся, сначала исправить или согласовать spec path; запрещено молча изобретать contract behavior.

### Git, Multica и lock-гейты
- Используй `$agent-issues` как источник истины для Multica issue-дисциплины, runtime `lockctl`, commit-гейты и движения worklog/status.
- Repo-local `AGENTS.md` может добавлять более строгие гейты конкретной области, но не должен дублировать полный Multica workflow.
- Push, deploy и publication требуют явного разрешения владельца или прямой команды `push/publish`.
- Работать только из чистого дерева, если владелец явно не разрешил работу поверх существующих несвязанных изменений; никогда не откатывать и не stage-ить несвязанные изменения пользователя.
### Кодирование и дисциплина изменений
- Делать минимальные точечные правки; сохранять существующую архитектуру, conventions и структуру файлов.
- Не добавлять speculative flexibility, широкие rewrites или unrelated cleanup.
- Перед исправлением воспроизвести или изучить проблему; перед завершением проверить, что запрошенный результат достигнут.
- Не менять production-состояние, не удалять данные, не reset-ить историю и не выполнять разрушительные операции без явного разрешения владельца.

### Процесс, пути и runtime
- Порядок process gates: Intake, Architecture, Implementation, Merge, QA, InfoSec, DevOps, Promotion.
- Не складывать мусор в `/int`; временные файлы должны лежать в `/int/.tmp/<ISO8601>/`.
- Переиспользуемый tooling должен жить в `/int/tools/**`.
- Канонические hosts: prod `vds.punkt-b.pro`, dev `vds.intdata.pro`.
- Канонические пользователи: `intdata` основной, `codex` runtime agent, `leon` manual-only.
- System roles и system tables Supabase нельзя менять.
- Frontend-диагностика и browser-proof по умолчанию идут через внутренний Codex Browser / Browser Use / in-app browser. Fallback только по фактическому blocker: `firefox-devtools`, затем `chrome-devtools`, затем standalone Playwright.
- Если существует repo-local или tooling machine-readable policy file, прочитай его. Если referenced machine policy file отсутствует, зафиксируй это как blocker или assumption, а не считай его доступным.
- Язык коммуникации — русский, если владелец явно не попросил иначе; фиксируй решения, blockers, verification и remaining risks.

## Политика frontend runtime
- Для сессий, стартующих из этого репозитория, default frontend-диагностика и browser-proof выполняются через внутренний Codex Browser / Browser Use / in-app browser.
- Fallback допускается только по blocker-case с явной фиксацией причины в handoff: сначала `firefox-devtools`, затем `chrome-devtools`, затем standalone Playwright.
# AGENTS — intTools

## Allowed scope

- `ops-tooling` contour для machine-wide automation;
- machine-wide ops/process/tooling, hooks, bootstrap scripts и shared runbooks;
- machine-wide delivery/process automation для top-level repo contours `/int/*`;
- внешние tooling contours для `intdata`, `crm`, `probe`, `codex` и соседних repos;
- repo-level docs по reusable tooling и host helpers.

## Владение источником истины

- `/int/tools` остаётся `ops-tooling` repo и владеет только reusable ops/process/tooling contour;
- business product-core и domain ownership остаются в соответствующих product repos;
- runtime state и реальные секреты живут вне tracked git; для intTools canonical ignored host path — `/int/tools/.runtime/**`.

## What not to mutate

- не складывать сюда canonical product domains и user-facing product shells;
- не использовать tracked repo как permanent runtime storage; ignored `/int/tools/.runtime/**` является локальным host-runtime исключением;
- не подменять локальные product README/AGENTS процессными копиями в tooling repo.

## Интеграционные ожидания

- reusable tooling хранится здесь, а не в корне `/int` и не в чужих product repos;
- product repos подключают этот contour извне через scripts, hooks и documented runbooks;
- self-authored/versioned Codex tooling и wrapper-скрипты должны жить в `/int/tools/codex/**`, а не в `~/.codex` / `C:\Users\intData\.codex`;
- custom intTools runtime state (`lockctl`, `gatesctl`, gate receipts, lock SQLite/events) должен жить в `/int/tools/.runtime/**`, а не в official Codex home (`~/.codex`, `C:\Users\intData\.codex`) и не в shared Codex memories; автоматические fallback/migration reads из `.codex/memories/**` запрещены.
- official Codex home (`~/.codex`, `C:\Users\intData\.codex`) является Codex-owned state: repo-owned scripts не должны копировать, зеркалить, патчить или генерировать туда overlay/config; изменения Codex home допустимы только через native documented Codex mechanisms или explicit manual owner action.
- reusable browser tooling, Firefox MCP launcher-ы и tracked project overlays живут только в `/int/tools/codex/**`;
- runtime layout для dedicated Firefox MCP contour документируется и поддерживается только из `/int/tools/codex/**` + `/int/tools/.runtime/firefox-mcp/**`;
- repo остаётся machine-wide tooling layer, а не отдельным business runtime.
- прямые кодовые импорты между `/int/tools` и другими top-level root-контурами `/int/*` запрещены; интеграция допустима только через documented scripts/hooks/CLI entrypoints, public APIs/contracts, events или иные явно согласованные boundary contracts.

## Триггеры эскалации

- попытка превратить `/int/tools` в owner business product-core;
- перенос mutable runtime-state или секретов в tracked repo;
- дублирование локальных product-docs вместо ссылок на реальные owner repos.

## Lock и Multica gates
- Используй `$agent-issues` как источник истины для Multica issue-дисциплины, runtime `lockctl`, commit-гейты и движения worklog/status.
- Любые файловые правки в этом repo запрещены без предварительного `lockctl acquire` по конкретному файлу; после завершения лок обязательно снимается через `lockctl release-path` или `lockctl release-issue`.
- Repo-local правила ниже могут ужесточать git/commit/publish flow, но не должны дублировать полный Multica workflow.

## Codex Skill Governance

- Для создания или правки любого `SKILL.md` агент обязан загрузить и соблюдать официальный `$skill-creator` до файловых изменений.
- Новые skills создаются через `skill-creator/scripts/init_skill.py`, если skill ещё не существует; ручное создание структуры допустимо только как явно зафиксированный blocker/fallback.
- После правки skill обязательно выполнить `skill-creator/scripts/quick_validate.py <path-to-skill-folder>` и исправить ошибки до commit/publish; на Windows запускать validator с `PYTHONUTF8=1`, чтобы Python не читал русскоязычный `SKILL.md` через cp1251.
- Перед копированием skill в `C:\Users\intData\.codex\skills` или иной Codex home проверить, что `SKILL.md` начинается с raw bytes `2D 2D 2D` (`---`) без UTF-8 BOM и содержит closing frontmatter delimiter.
- Не читать/перезаписывать русскоязычные `SKILL.md` через PowerShell default encoding; использовать явный UTF-8 без BOM или byte-level операции, чтобы не получить mojibake.

## Разделение документации

- `README.md` хранит только документацию и инструкции по репозиторию.
- `AGENTS.md` хранит только process/rules/gates/commit-policy этого repo.
- `RELEASE.md` ведётся опционально: обновляется только по прямому запросу владельца или в задаче на подготовку релиз-коммуникации.

## Tooling Mutation Governance

- Любая tracked-мутация repo-owned tooling в `/int/tools/**` обязана начинаться с согласованного OpenSpec package в `openspec/changes/<change-id>/`.
- Agents must use the `intdata-control` MCP plugin (`mcp__intdata_control__`) for OpenSpec discovery, validation, status, lifecycle, and gated mutation operations when available. Use read tools for discovery/status/validation and `openspec_change_mutate`, `openspec_spec_mutate`, or `openspec_exec_mutate` only for approved mutation workflows. Direct `openspec` CLI or repo-local `codex/bin/openspec*` usage is an explicit blocker/fallback path, not a PATH fallback.
- До первой tracked-правки должны существовать как минимум `proposal.md`, `tasks.md` и релевантный `spec.md` delta в `openspec/changes/<change-id>/specs/**`; `design.md` обязателен, если change меняет resolver/runtime architecture, capability boundaries или enforcement model.
- Каждый active OpenSpec change package должен явно указывать owning Multica issue в формате `INT-*`; соответствующий Multica issue/worklog должен ссылаться на путь `openspec/changes/<change-id>/`.
- OpenSpec остаётся источником истины для requirements/spec/acceptance, Multica остаётся источником истины для execution/worklog/status/blockers/closure; полный OpenSpec не зеркалится в issue, туда пишутся только short summary и links/paths.
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
  - plugin `intdata-control` (`intData Control`) заменяет `lockctl`, `openspec`, `intdata-governance`, `intdata-routing`, `intdata-delivery`, `gatesctl`;
  - plugin `intdata-runtime` заменяет `intdata-host`, `intdata-ssh`, `intdata-browser`, `intdata-vault`.
- Публичные tool names (без alias-совместимости):
  - governance: `routing_validate`, `routing_resolve`, `gate_status`, `gate_receipt`, `commit_binding`;
  - OpenSpec: `openspec_list`, `openspec_show`, `openspec_validate`, `openspec_status`, `openspec_instructions`, `openspec_new`, `openspec_archive`, `openspec_change_mutate`, `openspec_spec_mutate`, `openspec_exec_mutate`;
  - runtime: `host_preflight`, `host_verify`, `host_bootstrap`, `recovery_bundle`, `ssh_resolve`, `ssh_host`; browser testing defaults to internal Codex Browser / Browser Use / in-app browser, with fallback to `firefox-devtools-testing`, then `chrome-devtools`, then standalone Playwright (`browser_profile_launch` is deprecated compatibility only).
- Старые plugin IDs/tool names из удалённых шести плагинов не использовать в AGENTS/skills/runbooks.
- Canonical engine roots:
  - SSH / Firefox / host launchers: `codex/bin`
  - lockctl CLI/MCP: `lockctl/lockctl_core.py`, `codex/bin/mcp-intdata-cli.py --profile intdata-control`
  - intdb: `intdb/lib/intdb.py`

## Git и завершение работы

- Для любой задачи с файловыми мутациями в `/int/*` агент явно проверяет native git state: `git status --short --branch`, при необходимости `git fetch --prune origin`, и `git pull --ff-only` только на чистом дереве с корректным upstream и `behind>0`.
- Локальный `int_git_sync_gate` и MCP `sync_gate_*` удалены/запрещены; не используйте repo-owned sync wrappers вместо явных git-команд и hooks.
- Запрещено завершать задачу с локальными commit-ами `ahead>0`, если владелец не остановил задачу до публикации явно.
- Любая завершённая правка в `/int/tools` считается незавершённой, пока в пределах текущей задачи не создан как минимум один локальный commit в этом repo.
- Перед каждым локальным commit обязательно добавить в индекс новые файлы текущего scope и повторно выполнить `git add` для уже staged путей после каждой дополнительной правки; commit по устаревшему состоянию индекса запрещён.
- Перед каждым локальным commit обновление `RELEASE.md` не требуется; по умолчанию источник истины по изменениям — git history (commit subjects/body + diff).
- Релизный пост формируется по запросу из git-истории (commit subjects/body + diff) с ручной редактурой под целевую аудиторию.
- Если в задаче явно нужен релизлог, используем только корневой `RELEASE.md`; исторический `docs/`-путь и другие альтернативные варианты не используем.
- Перед локальным commit агент обязан проверить, не устарел ли корневой `README.md`; если правка меняет описанные там команды, структуру, маршруты, интеграции или инструкции, обновление `README.md` входит в тот же commit.
- Любой push в удалённую ветку `main` допустим только при `ALLOW_MAIN_PUSH=1` и только из локальной `main`.
- Для `/int/tools` owner-approved git-задача после локального commit и при чистом дереве должна завершаться немедленным native `git push origin main:main` в `origin/main`; локальный commit без этой публикации считается промежуточным состоянием, если владелец явно не остановил задачу до push.
- Если native publication в `origin/main` завершилась non-zero, задача считается незавершённой до устранения причины и повторного успешного push.
- Для каждого checkout/worktree обязателен локальный bootstrap `git config core.hooksPath .githooks`; tracked `.githooks/pre-push` включает этот guardrail только после такой настройки и не ограничивает push в `dev` или другие non-main branches.
- `git push` и прочие remote-операции остаются отдельным шагом и не выполняются автоматически без разрешения владельца или явного требования локального процесса.
- Локальный `git add`/`git commit` по умолчанию остаётся дисциплиной согласованного scope: агент коммитит свои/согласованные правки, если владелец явно не указал включить больше.
- Если владелец явно командует `push/publish/выкатывай/публикуй`, агент обязан либо выполнить явные native git/deploy команды по текущему documented process целевого repo, либо остановиться и спросить, что делать дальше при блокере/неоднозначности.
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
- `EXECUTE`: не открывать lifecycle/spec "на всякий случай"; любые мутации `openspec/**` запрещены без явного разрешения владельца.
- `PLAN`: читать только summary/headers и локальный контекст; любые мутации `openspec/**` запрещены без явного разрешения владельца.
- `SPEC-MUTATION`: применять lifecycle только если задача реально меняет contracts/API/schema/capability boundaries; любая мутация `openspec/**` допускается только по явному разрешению владельца, без самостоятельного "додумывания" несогласованных spec-деталей.
- `FINISH`: опираться только на локальный diff, результаты checks и состояние рабочей зоны; любые мутации `openspec/**` запрещены без явного разрешения владельца.

## Spec-First Policy
- Главный приоритет любой реализации — согласованная актуальная спека (OpenSpec / approved spec source-of-truth для контура).
- Для `/int/tools` OpenSpec обязателен не только для API/schema/capability work, но и для любых tracked tooling/process mutations: без active agreed `openspec/changes/<change-id>/` реализация запрещена.
- Если спеки нет, она неполная, противоречивая или не фиксирует API/contracts/capability boundaries, сначала нужно довести спеку до согласованного состояния и только потом приступать к реализации.
- Изменения API, RPC, schema contracts, payload shape, capability boundaries и access semantics без зафиксированной и согласованной спеки запрещены.
- Если реализация расходится со спекой, приоритет у спеки; сначала исправляется/уточняется spec source-of-truth, затем код.
- Любой owner-facing triage обязан явно ответить: какая спека является источником истины, полна ли она и разрешает ли текущую реализацию.
