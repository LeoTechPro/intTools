# Issue-id Driven GitHub Issue Flow

## Назначение
Этот регламент фиксирует обязательную привязку каждого коммита к конкретной GitHub Issue в мультиагентном «грязном» дереве без обязательного создания новых веток.

Ключевые инварианты:
- быстрый локальный `git commit` в `dev` допустим без live GitHub/lock/LLM gates;
- один issue-bound коммит связан только с одной issue;
- строгий branch-aware remote/barrier-контракт для fast/local-commit path живёт в `issue:push:done -- --issue <id>` и не является receipt-equivalent заменой обычного `gatesctl audit-range`;
- явный full-gate commit-контракт: `issue_commit.sh --issue <id>`; blocking `docs_sync` и auto-scope expansion разрешены только для full path;
- для `issue_commit --issue` каждый файл обязан иметь активный `lockctl` lease той же issue;
- отсутствие lease, истёкший lease и lease другой issue блокируют коммит;
- после любого коммита `post-commit` пытается снять lock только по файлам `HEAD` и только для issue из `Refs #<id>`;
- при отсутствии/невалидности `Refs #<id>` `post-commit` делает безопасный skip (`LOCK_RELEASE_SKIP`) без блокировки коммита;
- после успешного `issue_commit --issue` lock release дополнительно выполняется внутри скрипта как fallback/idempotent;
- локальные `Fixes/Closes/Resolves #...` запрещены;
- закрытие issue выполняется через `issue:done` или `issue:push:done`;
- `issue:done` перед закрытием всегда делает release всех активных `lockctl` locks по `GitHub issue id`;
- новые agent-docs вне `docs/process/**` и `docs/runbooks/**` запрещены;
- `docs/release.md` меняется только release issue с label `release`, а user-visible feature issue публикует текст через `label: release-note` + `## Release note`.

## Где работает
- локальный контур разработки (`/int/punctb`);
- рабочая ветка `dev`; `main` обновляется только owner-approved fast-forward promotion из уже существующего commit в `origin/dev`;
- GitHub Free/private (без rulesets/branch protection enforcement);
- versioned внутренний регламент хранится в `docs/process` и `docs/runbooks` (без публикации в `/docs/*`).
- GitHub Project не использует отдельную Actions-синхронизацию поля `Updation Date`: агенты поддерживают project-актуальность через `Status` и обязательный worklog в issue.

## Компоненты
- резолвер: `ops/issue/lock_issue_resolver.py`;
- branch-aware audit: `ops/issue/branch_policy_audit.py`;
- lock release: `ops/issue/lock_release_by_issue.py`;
- guard: `ops/gates/docs_boundary_guard.sh`;
- pre-commit gates: `ops/gates/docs_sync_gate.sh`, `ops/db/dba_review_gate.sh`, `ops/gates/autoreview_gate.sh`, `ops/teamlead/teamlead_orchestrator.sh`;
- guarded migration apply: `ops/db/migration_apply_gate.sh`;
- hooks: `git-hooks/commit-msg`, `git-hooks/pre-push`, `git-hooks/post-commit`, `git-hooks/reference-transaction`;
- CLI-скрипты: `ops/issue/issue_commit.sh`, `ops/issue/issue_done.sh`, `ops/issue/issue_audit_local.sh`, `ops/gates/gates_verify_commit.sh`, `ops/gates/gates_verify_push.sh`, `ops/gates/gates_bind_commit.sh`, `ops/issue/install_issue_hooks.sh`, `ops/release/release_prepare.sh`, `ops/release/release_main.sh`;
- CI fallback: `.github/workflows/issue-link-audit.yml`.

## Предусловия
1. `gh` авторизован (`gh auth status`).
2. Hooks установлены (дополнительный барьер, включая branch-creation guard):
```bash
npm run issue:hooks:install
```
3. Machine-wide source-of-truth по локам: shell-команда `lockctl`; implementation-файл лежит в `/int/tools/lockctl/lockctl.py`, repo-local wrapper — `/int/tools/lockctl/lockctl`, а каталог `/int/tools/lockctl` не является исполняемым файлом.
4. Для PunctB любой write-scope должен быть предварительно закрыт активными `lockctl` lease-locks с числовым `GitHub issue id`.

## Контракт `lockctl`
- один активный writer-lock на файл;
- ключ блокировки = `(repo_root, path_rel)`;
- для PunctB `issue_id` обязателен и равен числовому `GitHub issue id`;
- активность определяется `expires_utc > now_utc`;
- просроченный lease не является truth и требует нового `lockctl acquire`.

## Алгоритм fast local commit
1. Обычный `git commit` в `dev` проходит только дешёвые локальные проверки:
   - ветка `dev/main`;
   - запрет `Fixes/Closes/Resolves #...`;
   - блокировка явных risky-targets (`docs/release.md`, migration scope).
2. Fast-path не требует:
   - live GitHub issue;
   - `lockctl assert`;
   - `docs_sync`;
   - `autoreview`;
   - `teamlead` orchestration.
3. Перед push такой commit-range всё равно обязан пройти `issue:push:done`.
4. Для push-ready range каждый коммит уже должен содержать `Refs #<issue_id>`; `issue:push:done` не переписывает commit messages и не добивает `Gate-Receipt/Gate-Policy` trailers задним числом.

## Алгоритм `issue_commit --issue`
1. Принимается явный `--issue <id>` и проверяется через `gh issue view` (`OPEN`).
2. Берутся фактические файлы коммита (`--files`/`--file`).
3. `lock_issue_resolver.py assert-issue-files` требует активный `lockctl` lease на каждый файл под той же issue:
   - `NO_LOCK` -> блок;
   - `LOCK_EXPIRED` -> блок;
   - `LOCK_CONFLICT` -> блок.
4. Без `--full` `docs_sync_gate.sh` работает только в advisory-режиме и не мутирует соседние README/process docs.
5. С `--full` `docs_sync_gate.sh` работает в blocking-режиме; auto-updated docs вне явного scope требуют явного `--expand-doc-targets`.
6. Если scope содержит `backend/init/migrations/**` или `backend/init/migration_manifest.lock`, commit-path разрешён только через `--full`, а review идёт через `dba_review_gate.sh`.
7. Для risky/full scope запускается `autoreview_gate.sh`; pure process/docs-only scope по умолчанию не тянет LLM-review на commit-time.
8. `teamlead_orchestrator.sh --mode milestone` обязателен только для `--full` major/risky scope или при явном форсинге.
9. Только после зелёного full-loop `docs_boundary_guard.sh` запрещает новые `docs/**` файлы и любые tracked internal docs внутри product repo; runtime-артефакты должны оставаться только в `~/.codex/tmp/punctb/**`.
10. `branch_policy_audit.py validate-staged` подтверждает ветку `dev` и разрешает изменение `docs/release.md` только issue с label `release`.
11. `gates_verify_commit.sh` вызывает global `gatesctl verify --stage commit`, проверяет обязательный receipt и возвращает `receipt_id`, `policy_version`, `scope_fingerprint`.
12. `Refs #<id>` добавляется/валидируется через `ensure-message`, после чего в commit message обязательно дописываются `Gate-Receipt: <receipt_id>` и `Gate-Policy: <policy_version>`.
13. Выполняется commit только целевых файлов, включая явно разрешённые auto-updated docs/manifest внутри issue scope.
14. Сразу после успешного коммита `gates_bind_commit.sh` привязывает receipt к фактическому `commit_sha`, а `post-commit` повторяет bind как best-effort fallback для ручных путей.
15. После bind `post-commit` вызывает `lock_release_by_issue.py` и снимает lock только по путям `HEAD`; `issue_commit.sh` дополнительно делает тот же release как fallback/idempotent слой.

## Алгоритм `migration_apply_gate --issue`
1. Принимается явный `--issue <id>` и migration-only scope (`backend/init/migrations/*`, `backend/init/migration_manifest.lock`).
2. Если manifest не передан явно, скрипт автоматически добавляет `backend/init/migration_manifest.lock` в scope.
3. `lock_issue_resolver.py assert-issue-files` требует активный `lockctl` lease той же issue на каждый файл migration scope, включая auto-added manifest.
4. `dba_review_gate.sh` выполняет dual DBA review и manifest/layout consistency checks.
5. Только после `DBA_REVIEW_OK` запускается команда применения миграций; по умолчанию это `bash backend/init/010_supabase_migrate.sh`.
6. Сам bootstrap-скрипт мигратора остаётся runtime-only и не вызывает `codex` напрямую.

## Алгоритм `autoreview_gate --issue`
1. Принимается явный `--issue <id>` и scope через `--files`/`--file` или `--range`.
2. Проверяет обязательные runtime-зависимости: `codex`, schema `AUTOREVIEW_SCHEMA_FILE` и risk-matrix `SWARM_RISK_MATRIX_FILE`.
3. Для migration scope сразу завершает работу с `HUMAN_GATE_REQUIRED`; этот путь должен идти через `dba_review_gate.sh`.
4. По матрице scope вычисляет `required_checks` и сначала прогоняет conventional checks:
   - web/docs scope: `build`, path-aware `lint`, scoped `unit`;
   - process-contract scope (`README.md`, `package.json`, `.gitignore`, `AGENTS.md`, `GEMINI.md`, `openspec/**`): локальный syntax-lint;
   - неподдержанные проверки получают `skipped`, а реально недоступные обязательные проверки дают `CHECK_UNAVAILABLE`.
5. Если любой обязательный check падает, gate завершает работу с `CHECK_FAILED` до LLM-review.
6. При зелёных checks запускает `reviewer_a` в read-only; при `request_changes` допускает один fixer-pass в workspace-write только по scope и повторяет цикл до лимита.
7. Только после `ok` от reviewer A запускает независимый `reviewer_b`; его `request_changes` тоже переводит gate в следующий bounded fixer-цикл.
8. Итоговый summary всегда пишется в `~/.codex/tmp/punctb/autoreview/<issue>/<timestamp>/final-gate.json` с `reason`, `attempts_used`, `required_checks` и метаданными checks.
9. Основные причины отказа: `CHECK_FAILED`, `CHECK_UNAVAILABLE`, `HUMAN_GATE_REQUIRED`, `REVIEWER_*`, `FIXER_AFTER_REVIEWER_*`, `MAX_ATTEMPTS_EXCEEDED`.

## Алгоритм `teamlead_orchestrator`
1. Классифицирует scope через `ops/teamlead/role_opinion_matrix.py` и `templates/swarm-risk-matrix.yaml`.
2. Вычисляет `required_checks`, `required_opinions`, `major_change`, `auto_commit_eligible`.
3. Запускает независимые role-opinions через `codex exec --ephemeral` без shared transcript.
4. В `milestone` режиме допускает один bounded fix loop внутри scope и перезапускает только проблемные роли.
5. В `finish` режиме работает только read-only и блокирует `issue:push:done`, если role-opinions не зелёные.

## Алгоритм `issue_done --issue`
1. Проверка, что у issue нет незапушенных локальных коммитов с `Refs #<id>`.
2. Проверка, что GitHub issue находится в состоянии `OPEN`.
3. По умолчанию — проверка bound `gatesctl` receipt у последнего issue-коммита; если `issue_done` вызван из `issue:push:done`, эта проверка пропускается, потому что branch-aware strict push-gate уже выполнен и подтверждён scoped approval artifact для того же `repo/branch/issue/last_issue_commit`.
4. Обязательный release всех активных `lockctl` locks по `issue_id = GitHub issue id`.
5. Закрытие issue через `gh issue close`.

## Алгоритм release-path
1. Для заметной пользователю задачи в обычной feature/bug issue хранится публичный текст в `## Release note`, а issue получает label `release-note`.
2. Для выпуска создаётся отдельная `OPEN` release issue с label `release` и секцией `## Release includes` (или `## Included issues`) со списком включаемых issue-id.
3. `npm run release:prepare -- --issue <release_issue_id>` работает только на `dev`, собирает `docs/release.md` из закрытых `release-note` issues и коммитит файл через `issue:commit --full --expand-doc-targets` под release issue.
4. `PUNCTB_MAIN_PUSH_APPROVED=YES npm run release:main -- --issue <release_issue_id> [--sha <commit>]` проверяет clean tree, fast-forward topology `main`, достижимость target SHA из `origin/dev`, branch-aware main audit и только затем делает `git push origin <sha>:main`.
5. После успешного promotion release issue закрывается отдельным комментарием о выпущенном SHA.

## Базовый рабочий цикл
1. Взять `lockctl acquire` на файлы задачи до начала правок.
2. Убедиться, что hooks установлены (дополнительный барьер):
```bash
npm run issue:hooks:install
```
3. Для быстрых локальных шагов допустим обычный `git commit`; для fully-gated/risky scope используйте `issue:commit`:
```bash
git commit -m "wip: локальная правка" -m "Refs #1037"
```
4. Сделать fully-gated issue-bound commit только целевых файлов при необходимости:
```bash
npm run issue:commit -- --issue 1037 --message "web: update profile toolbar" --files "web/src/a.tsx,web/src/b.tsx"
```
5. Для реального применения migration scope используйте guarded wrapper:
```bash
npm run migration:apply:guarded -- --issue 1214 --files "backend/init/migrations/20260310201500_client_home_public_surface.sql,backend/init/migration_manifest.lock"
```
6. Проверить диапазон перед push:
```bash
npm run issue:audit:local -- --range "@{upstream}..HEAD"
```
7. Если acceptance checklist в issue полностью выполнен, выполнить единый remote-финиш:
```bash
npm run issue:push:done -- --issue 1037
```
8. Если нужен ручной режим, оставить раздельные шаги:
```bash
git push origin dev
npm run issue:done -- --issue 1037
```

## Release-only changelog workflow
1. В feature issue подготовить `label: release-note` и секцию `## Release note`.
2. Создать отдельную release issue с label `release` и списком включаемых issue.
3. На `dev` выполнить:
```bash
npm run release:prepare -- --issue 1205
```
4. После review и owner-approved promotion выполнить:
```bash
PUNCTB_MAIN_PUSH_APPROVED=YES npm run release:main -- --issue 1205
```

## Finish: local vs remote
- Команда владельца «Завершайся» закрывает локальный цикл: проверки, документация/worklog, локальный commit-path и cleanup `~/.codex/tmp/punctb`.
- Fast local commits в `dev` допустимы, но перед push итоговый range обязан пройти `issue:push:done`.
- `issue:commit` обязан выпустить bound receipt через `gatesctl verify -> Gate-Receipt/Gate-Policy -> bind-commit`; lock для коммитнутых путей снимается через `post-commit`, а в `issue:commit` сохранён fallback release.
- При закрытии через `issue:done` дополнительно снимаются оставшиеся активные `lockctl` locks по `GitHub issue id`.
- Если acceptance checklist выполнен и нет `owner_choice_required`, следующий обязательный шаг процесса — `npm run issue:push:done -- --issue <id>`.
- При необходимости допускается ручной split: `git push` и `issue:done` отдельными командами.
- `issue:done` и `issue:push:done` не используются в `main`; release-flow закрывается через `release:main`.
- Если issue добавлена в GitHub Project, перед handoff агент обновляет `Status` и пишет worklog; отдельное поле `Updation Date` вручную не поддерживается.

## Поведение hooks
### `commit-msg`
- dev/main fast-path для ручного `git commit`;
- запрещает `Fixes|Closes|Resolves #...`;
- блокирует явные risky-targets: `docs/release.md`, `backend/init/migrations/**`, `backend/init/migration_manifest.lock`;
- не требует live GitHub issue, `lockctl`, `docs_sync`, `autoreview` или `teamlead`;
- не участвует в release-path, потому что `release:prepare` и `issue:commit` коммитят через `--no-verify`.

### `reference-transaction`
- блокирует создание новых локальных веток без явного owner override;
- не блокирует только узкий bootstrap локальной `dev`, когда новая ветка создаётся ровно на текущем tip `origin/dev` (`git switch -c dev --track origin/dev`);
- разрешает только `PUNCTB_ALLOW_NEW_BRANCH=YES` и опциональный `PUNCTB_ALLOW_BRANCH_NAME=<name>`;
- не влияет на обновление существующих веток и не участвует в release-path напрямую.

### `pre-push`
- проверяет все коммиты, уходящие на remote;
- блокирует push в ветки кроме `dev` и `main`;
- требует явный owner-approved override для push в `main`;
- для `dev` требует ровно один `Refs #<id>` на коммит и `OPEN` issue;
- для `main` разрешает closed issues, но требует fast-forward topology и достижимость target SHA из `origin/dev`;
- применяет docs/agent boundary guard к range перед push;
- для `dev/main` дополнительно запускает `gates_verify_push.sh` / `gatesctl audit-range`; scoped approval artifact от `issue:push:done` допускается только для его собственного `git push`.

### `post-commit`
- извлекает issue из `Refs #<id>` последнего коммита (`HEAD`) через `verify-commit`;
- best-effort вызывает `gates_bind_commit.sh` для привязки `Gate-Receipt` к `HEAD`, если commit был создан не через основной wrapper или bind ещё не успел выполниться;
- берёт список файлов коммита `HEAD` и запускает `lock_release_by_issue.py`;
- при невалидном/отсутствующем `Refs` печатает `LOCK_RELEASE_SKIP` и завершается с кодом `0`;
- при ошибке lock-release печатает `LOCK_RELEASE_WARN` и не блокирует завершённый коммит.

## Команды и назначение
- `npm run issue:hooks:install` — установка hooks.
- `npm run issue:commit -- --issue <id> --message "..." --files "a,b"` — explicit issue-bound commit path; без `--full` держит `docs_sync` advisory-only и не запускает commit-time heavy gates для pure process/docs scope.
- `npm run issue:audit:local -- --range "origin/dev..HEAD"` — локальный dev-only аудит commit-range с branch-policy и, по умолчанию, `gatesctl audit-range`.
- `npm run issue:push:done -- --issue <id>` — dev-only strict push gate для fast/local-commit path: branch-aware one-issue range audit + acceptance checklist + lock conflicts + blocking `docs_sync` + risk-based `autoreview` + `teamlead` finish + scoped approval artifact для конкретных `repo/branch/range/issue/last_issue_commit` + push + close issue.
- `npm run issue:done -- --issue <id>` — dev-only явное закрытие issue после push; по умолчанию требует bound receipt, а при вызове из `issue:push:done` принимает только scoped approval artifact той же issue, того же `last_issue_commit` и всегда чистит lock по `GitHub issue id`.
- `npm run migration:apply:guarded -- --issue <id> --files "migration.sql,backend/init/migration_manifest.lock"` — dual-DBA-gated запуск применения миграций.
- `npm run teamlead:orchestrate -- --issue <id> --mode milestone|finish --files "a,b"` — teamlead-first orchestration независимых role-opinions.
- `bash ops/gates/gates_verify_commit.sh --issue <id> --files "a,b"` — thin wrapper над global `gatesctl verify --stage commit`.
- `bash ops/gates/gates_verify_push.sh --range "@{upstream}..HEAD"` — thin wrapper над global `gatesctl audit-range`.
- `bash ops/gates/gates_bind_commit.sh --issue <id> --commit <sha> --receipt <id>` — привязка receipt к коммиту и issue-audit trail.
- `npm run release:prepare -- --issue <release_issue_id>` — собрать и закоммитить release-only запись в `docs/release.md`.
- `PUNCTB_MAIN_PUSH_APPROVED=YES npm run release:main -- --issue <release_issue_id>` — fast-forward promotion `origin/dev` -> `main`.
- `bash ops/gates/docs_boundary_guard.sh --staged --allow-owner-override` — hard gate на новые файлы в `docs/**`.

## CI fallback (`issue-link-audit.yml`)
Workflow запускается на `push` и `pull_request`:
- вычисляет commit-range;
- определяет target branch (`dev` или `main`);
- применяет docs/agent boundary guard к range;
- запускает branch-aware issue audit: `dev` требует `OPEN`, `main` проверяет release-topology без требования `OPEN`.

Назначение: страховка на случай обхода hooks (`--no-verify`, новый клон без установки hooks).

## Мультиагентные сценарии
1. Грязное дерево допустимо, если коммит делается только по своим файлам через `issue:commit --issue`.
2. Один и тот же файл в активных lock-записях разных issue блокирует коммит до разрешения коллизии.
3. Просроченный lease блокирует `issue:commit --issue` до нового `lockctl acquire`.
4. Отсутствие активного `lockctl` lease блокирует `issue:commit --issue`.

## Коды ошибок
Основные коды:
- `LOCK_CONFLICT`
- `NO_LOCK`
- `LOCK_EXPIRED`
- `AMBIGUOUS_LOCK`
- `MULTI_ISSUE`
- `MISSING_REFS`
- `MISMATCH_REFS`
- `FORBIDDEN_CLOSE_KEYWORD`
- `ISSUE_NOT_FOUND`
- `ISSUE_NOT_OPEN`

## Запрещено
- Коммиты с `Fixes/Closes/Resolves #...`.
- Коммит файлов, принадлежащих разным issue.
- Закрытие issue без проверки синхронизации и без release активных locks по `GitHub issue id` (`issue:done` делает это автоматически).
- Создание новых файлов в `docs/**` без owner override (`PUNCTB_DOCS_OWNER_APPROVED=YES`).
- Прямые рабочие коммиты в `main`.
- Изменение `docs/release.md` вне release issue с label `release`.

## Диагностика проблем
1. Проверить, что выбранный issue не конфликтует с активными lock по файлам:
```bash
python3 ops/issue/lock_issue_resolver.py assert-issue-files --issue-id 1037 --files path/to/file --check-gh --require-open --json
```
2. Проверить resolve по текущим `lockctl` leases:
```bash
python3 ops/issue/lock_issue_resolver.py resolve --files path/to/file --check-gh --require-open
```
3. Проверить конкретный commit:
```bash
python3 ops/issue/lock_issue_resolver.py verify-commit --commit <sha> --check-gh --require-open
```
4. Проверить диапазон:
```bash
python3 ops/issue/branch_policy_audit.py audit-range --target-branch dev --range "@{upstream}..HEAD"
```

## Краткий чек-лист перед push
1. Для файлов коммита нет активного lock-конфликта с другой issue.
2. Коммит выполнен через `issue:commit --issue <id>`.
3. `issue:audit:local` зелёный.
4. В commit message есть ровно один `Refs #<id>`.
