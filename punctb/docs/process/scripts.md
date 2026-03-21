# Скрипты AGENTS

## smoke_workspace_dashboard.js
Playwright‑смоук для workspace‑дашборда и редиректов:
- вход по `/lk`
- проверка `Панель рабочей области` на `/`
- редиректы `/manager`, `/specialist` -> `/`
- редирект `/client` -> `/diag`

### Требования
- Установлен `@playwright/test` (есть в repo).
- Установлены браузеры Playwright (`npx playwright install`).
- Локальный dev-контур доступен (по умолчанию `https://dev.punctb.pro`).

Если Playwright сообщает о нехватке системных библиотек — согласовать установку зависимостей с владельцем/DevOps.

### Запуск
```bash
BASE_URL=https://dev.punctb.pro \
WORKSPACE_EMAIL=manager.example@punctb.test \
WORKSPACE_PASSWORD='******' \
node ops/qa/smoke_workspace_dashboard.js
```

### Выходы
- `SMOKE_OK` — проверка пройдена.
- `SMOKE_FAIL` — проверка не пройдена (подробности в сообщении).

## agent_browser_role_smoke.sh
Role-based smoke через `agent-browser` для `client/specialist/admin`:
- вход под тремя ролями в изолированных browser sessions;
- проверка базовых allowed/blocked маршрутов;
- фиксация deny-паттернов (`section/workspace/404`);
- генерация JSON-отчёта с check-id и pass/fail.

### Требования
- Установлен `agent-browser`:
  - `npm install -g agent-browser`
  - `agent-browser install`
- Доступны тестовые аккаунты и пароль.

### Параметры (env, optional)
- `BASE_URL` (default `https://dev.punctb.pro`)
- `WORKSPACE_PASSWORD` (default `<SECRET>`)
- `ADMIN_EMAIL` (default `admin.demo@punctb.test`)
- `SPECIALIST_EMAIL` (default `specialist.demo@punctb.test`)
- `CLIENT_EMAIL` (default `client.demo@punctb.test`)
- `REPORT_PATH` (default `~/.codex/tmp/punctb/agent_browser_role_smoke_<UTC>.json`)

### Запуск
```bash
bash ops/agent-browser/agent_browser_role_smoke.sh
```

Пример с явными env:
```bash
BASE_URL=https://dev.punctb.pro \
WORKSPACE_PASSWORD='******' \
ADMIN_EMAIL='admin.demo@punctb.test' \
SPECIALIST_EMAIL='specialist.demo@punctb.test' \
CLIENT_EMAIL='client.demo@punctb.test' \
bash ops/agent-browser/agent_browser_role_smoke.sh
```

### Выходы
- `SMOKE_OK` — role-smoke пройден.
- `SMOKE_FAIL` — есть проваленные check-id.
- `REPORT_PATH=...` — путь к JSON-отчёту (всегда печатается).

## agent_browser_key_scenarios.sh
Прицельный сценарный прогон через `agent-browser` по приоритетным потокам:
- клиент (авторизованный): полное прохождение диагностики `43 профессии` до `/diag/testing-end`;
- клиент (новый, публичный путь): заполнение анкеты по ссылке специалиста и проверка server-side ошибок;
- специалист: назначение диагностик, результаты, клиенты, выдача заключения;
- админ: доступ к `/users`, создание пользователя, контроль наличия грант/ревок-контролов.

### Требования
- Установлен `agent-browser`:
  - `npm install -g agent-browser`
  - `agent-browser install`
- Доступны тестовые аккаунты и пароль.

### Параметры (env, optional)
- `BASE_URL` (default `https://dev.punctb.pro`)
- `WORKSPACE_PASSWORD` (default `<SECRET>`)
- `ADMIN_EMAIL` (default `admin.demo@punctb.test`)
- `SPECIALIST_EMAIL` (default `specialist.demo@punctb.test`)
- `CLIENT_EMAIL` (default `client.demo@punctb.test`)
- `PUBLIC_CLIENT_FIRST_NAME` (default `Тестовый`)
- `PUBLIC_CLIENT_FAMILY_NAME` (default `Клиент`)
- `PUBLIC_CLIENT_PHONE` (default `+7 900 000 00 00`)
- `PUBLIC_CLIENT_EMAIL` (default `public.demo@punctb.test`)
- `REPORT_PATH` (default `~/.codex/tmp/punctb/agent_browser_key_scenarios_<UTC>.json`)

### Запуск
```bash
bash ops/agent-browser/agent_browser_key_scenarios.sh
```

Пример с явными env:
```bash
BASE_URL=https://dev.punctb.pro \
WORKSPACE_PASSWORD='******' \
ADMIN_EMAIL='admin.demo@punctb.test' \
SPECIALIST_EMAIL='specialist.demo@punctb.test' \
CLIENT_EMAIL='client.demo@punctb.test' \
PUBLIC_CLIENT_EMAIL='public.demo@punctb.test' \
bash ops/agent-browser/agent_browser_key_scenarios.sh
```

### Выходы
- `SCENARIOS_OK` — все ключевые сценарии прошли.
- `SCENARIOS_FAIL` — есть проваленные check-id.
- `REPORT_PATH=...` — путь к JSON-отчёту (всегда печатается).

## agent_browser_gate.sh
Процессный gate-раннер для внедрения `agent-browser` в role-пайплайн:
- `handoff`: быстрый pre-handoff gate (`role_smoke`);
- `full`/`release`: `role_smoke` + `key_scenarios`;
- `nightly`: `role_smoke` + `key_scenarios` по расписанию.

### Параметры (env, optional)
- `MODE` (`handoff` default): `handoff | full | release | nightly`
- `REPORT_PREFIX` (default `~/.codex/tmp/punctb/agent_browser_gate_<UTC>`)
- `SUMMARY_PATH` (default `${REPORT_PREFIX}_summary.json`)
- `ALLOW_NIGHTLY_SOFT_FAIL` (default `0`): только для `nightly`, не роняет job при fail `key_scenarios`.

### Запуск
Pre-handoff (обязательный быстрый gate):
```bash
MODE=handoff bash ops/agent-browser/agent_browser_gate.sh
```

Релизный/полный прогон:
```bash
MODE=full bash ops/agent-browser/agent_browser_gate.sh
```

Nightly (жёсткий):
```bash
MODE=nightly bash ops/agent-browser/agent_browser_gate.sh
```

Nightly (soft-fail, только если нужен отчёт без падения пайплайна):
```bash
MODE=nightly ALLOW_NIGHTLY_SOFT_FAIL=1 bash ops/agent-browser/agent_browser_gate.sh
```

### Выходы
- `GATE_OK` / `GATE_FAIL`
- `SUMMARY_PATH=...` — JSON summary c путями к отчётам role/key сценариев.
- `ROLE_REPORT=...`, `KEY_REPORT=...` — пути к детальным отчётам.

## smoke_api_access.sh
Базовый API/Edge smoke для раннего детекта 400/403:
- проверка PostgREST (`/rest/v1/user_profiles?select=id&limit=1`) под service key;
- проверка health Edge Function `main`;
- проверка валидации `create-user` (ожидаемый `400`, что подтверждает доступность endpoint и исполнение функции).

### Требования
- `curl`
- переменная окружения `SERVICE_ROLE_KEY`
- (опционально) `API_BASE_URL`, `API_HOST_HEADER`, `REQUEST_TIMEOUT`

### Запуск
```bash
API_BASE_URL=https://api-dev.punctb.pro \
SERVICE_ROLE_KEY='******' \
bash ops/qa/smoke_api_access.sh
```

### Выходы
- `SMOKE_OK` — все API/Edge проверки пройдены.
- `SMOKE_FAIL` — ошибка кода ответа/доступности (выводит тело ответа).

## run_notification_delivery_worker.sh
Триггерит одну итерацию business-email worker:
- вызывает `POST /functions/v1/notification-delivery-worker?limit=20`;
- использует service key из root `.env`.

### Требования
- заполнен root `.env` (`SUPABASE_PUBLIC_URL`, `SERVICE_ROLE_KEY`);
- поднят контейнер `supabase-edge-functions`.
- при нестабильном маршруте через Kong можно задать `API_BASE_URL=http://127.0.0.1:8900`.

### Параметры (env, optional)
- `API_BASE_URL` — переопределяет базовый URL вызова worker.
- `DELIVERY_WORKER_ATTEMPTS` (default `6`) — число retry при 502/503.
- `DELIVERY_WORKER_RETRY_DELAY_SEC` (default `2`) — пауза между retry.

### Запуск
```bash
bash ops/db/run_notification_delivery_worker.sh
```

### Выходы
- `notification-delivery-worker: ok ...` — вызов успешен.
- non-zero код — ошибка вызова/авторизации.

## check_notification_delivery_health.sh
Локальный watchdog по SMTP-доставке и auth-timeout:
- проверяет queue lag (`queued` email deliveries);
- считает fail-rate по `app.event_notification_deliveries`;
- проверяет количество `request_timeout/504` в логах `supabase-auth`.

### Требования
- локальный доступ к БД через `sudo -u postgres psql`;
- доступ к Docker логам контейнера `supabase-auth`;
- root `.env` или fallback на `.env.example`.

### Пороги (env, optional)
- `QUEUE_LAG_THRESHOLD_MIN` (default `15`)
- `FAIL_WINDOW_MIN` (default `15`)
- `FAIL_RATE_THRESHOLD_PCT` (default `30`)
- `FAIL_RATE_MIN_TOTAL` (default `5`)
- `AUTH_TIMEOUT_WINDOW_MIN` (default `15`)
- `AUTH_TIMEOUT_THRESHOLD` (default `1`)
- `AUTH_CONTAINER` (default `supabase-auth`)

### Запуск
```bash
bash ops/db/check_notification_delivery_health.sh
```

### Выходы
- `delivery-health: OK` + exit `0` — пороги не превышены.
- `delivery-health: ALERT` + exit `1` — превышен хотя бы один порог.

## check_migrations_consistency.sh
Сверка активных миграций в `backend/init/migrations` с применёнными версиями и lock-manifest `backend/init/migration_manifest.lock`.
Скрипт работает только в режиме detect/fail и проверяет:
- `manifest integrity` — валидность строк, отсутствие дублей и stale-записей;
- `checksum` — совпадение `sha256` файла миграции и manifest;
- `single-version rule` — в каждом активном SQL ровно один `INSERT INTO public.schema_migrations` и версия в SQL совпадает с префиксом файла;
- `missing` — активная версия есть в репозитории/manifest, но отсутствует в БД;
- `unmanaged extra` — версия есть в БД, но отсутствует и в active, и в archive;
- `duplicates` — дубли версий в файлах и `schema_migrations`.

### Требования
- локальный доступ к БД через `sudo -u postgres psql`
- база берётся из root `.env` (`POSTGRES_DB`), fallback: `.env.example`, затем `intdata`
- lock-manifest `backend/init/migration_manifest.lock`
- нижняя граница анализа версий (`VERSION_FLOOR`, по умолчанию `20260126000000`)

### Запуск
```bash
DB_NAME="$(grep -E '^POSTGRES_DB=' .env | tail -n1 | cut -d= -f2-)" \
VERSION_FLOOR=20260126000000 \
MANIFEST_FILE=backend/init/migration_manifest.lock \
bash ops/db/check_migrations_consistency.sh
```

### Выходы
- `SMOKE_OK` — manifest/checksum/single-version/active-sync проверки пройдены.
- `SMOKE_INFO` — обнаружены версии, применённые из `archive` (информационно).
- `SMOKE_FAIL` — перечисляет все категории несогласованности и завершает с non-zero кодом.

## smoke_rls_grants_matrix.sh
Read-only smoke-матрица для RLS/GRANT (без auto-remediation):
- проверяет наличие таблиц и состояние RLS (`relrowsecurity`) по критичным сущностям;
- проверяет наличие хотя бы одной policy для каждой критичной таблицы;
- проверяет обязательный (`required`) GRANT EXECUTE для ключевых helper-функций у роли `authenticator`.
- в текущем baseline проверяет `app.user_profiles`, `app.event_notifications`, `app.user_conclusions`.

### Требования
- локальный доступ к БД через `sudo -u postgres psql`
- база берётся из root `.env` (`POSTGRES_DB`), fallback: `.env.example`, затем `intdata`

### Запуск
```bash
DB_NAME="$(grep -E '^POSTGRES_DB=' .env | tail -n1 | cut -d= -f2-)" \
bash ops/db/smoke_rls_grants_matrix.sh
```

### Выходы
- `PASS`/`FAIL` по каждой строке матрицы.
- `SMOKE_OK` — все проверки матрицы пройдены.
- `SMOKE_FAIL` — найдено одно или более нарушений.

## swarm_policy_check.sh
Локальная policy-проверка для мультиагентного Git-процесса:
- определяет `highest_risk` по матрице путей;
- вычисляет обязательные проверки (`required_checks`);
- валидирует, что переданы все завершённые проверки;
- в режиме `degraded` требует аудируемый exception-файл.

### Артефакты
- матрица: `templates/swarm-risk-matrix.yaml`
- exception: `templates/swarm-exception.yaml`
- lock-шаблон: `templates/swarm-lock.yaml`
- регламент: `docs/process/git-swarm-reglament.md`

### Запуск (hard)
```bash
bash ops/gates/swarm_policy_check.sh \
  --files "web/src/main.tsx,backend/functions/foo/index.ts" \
  --completed "lint,build,unit,integration,security" \
  --mode hard
```

### Запуск (degraded, рискованно: только после ручной проверки)
```bash
bash ops/gates/swarm_policy_check.sh \
  --files "backend/init/migrations/20260213001000_revoke_legacy_referral_overloads.sql" \
  --completed "lint,build,unit,integration,migration-dry-run,rollback-rationale" \
  --mode degraded \
  --exception templates/swarm-exception.yaml
```

### NPM-обёртка
```bash
npm run policy:swarm -- \
  --files "docs/release.md" \
  --completed "lint,build"
```

### Выходы
- `POLICY_OK` — policy-gate пройден.
- `POLICY_FAIL` — отсутствуют обязательные проверки или invalid exception.

## safe_autopush.sh
Безопасный queue-based автопуш вместо `git add -A`:
- обрабатывает только явные заявки `~/.codex/tmp/punctb/autopush/*.env`;
- требует в заявке `ISSUE_ID` и коммитит только список `FILES` через `ops/issue/issue_commit.sh --issue <id>`;
- блокирует выполнение при несвязанных грязных файлах;
- выполняет локальный `codex` review по diff заявленных файлов и блокирует push при `fail`;
- запрещает high-risk пути (`backend/init/migrations`, `.beads`, infra compose);
- перед push выполняет `issue_audit_local.sh` на диапазон нового коммита;
- перед push выполняет `git fetch origin dev` и допускает продолжение только если `dev` синхронизируется fast-forward without rebase/merge;
- `TARGET_BRANCH=main` не поддерживается.

### Статус
Выключен по умолчанию. Любые git-действия возможны только при явном opt-in владельца; фоновые cron-запуски не используются.

### Запуск (только opt-in)
```bash
PUNCTB_GIT_APPROVED=YES ENABLE_SAFE_AUTOPUSH=1 bash ops/issue/safe_autopush.sh
```

### Формат заявки
```bash
REQUEST_ID=shared-org.193.frontend
ISSUE_ID=1037
COMMIT_MESSAGE=web: safe autopush batch
FILES=web/src/App.tsx,web/src/Sidebar.tsx
```

Подробнее: `docs/process/autopush.md`.

## lock_issue_resolver.py
Единый резолвер `lockctl` -> issue и валидатор commit metadata:
- читает machine-wide `lockctl` truth через shell-команду `lockctl`;
- определяет issue-id по активным lease-locks для `resolve` / `resolve-staged`;
- для `assert-issue-files` требует активный lease под той же issue на каждый файл;
- проверяет commit message на `Refs #<id>` и запрет `Fixes|Closes|Resolves`;
- валидирует issue через `gh issue view`.

### Запуск
```bash
# issue для staged файлов
python3 ops/issue/lock_issue_resolver.py resolve-staged --check-gh --require-open

# issue для явного списка файлов
python3 ops/issue/lock_issue_resolver.py resolve --files web/src/a.tsx web/src/b.tsx --check-gh --require-open

# conflict-only проверка для explicit issue
python3 ops/issue/lock_issue_resolver.py assert-issue-files --issue-id 1037 --files web/src/a.tsx web/src/b.tsx --check-gh --require-open --json

# аудит диапазона коммитов
python3 ops/issue/lock_issue_resolver.py audit-range --range "@{upstream}..HEAD" --check-gh --require-open
```

### Коды ошибок (основные)
- `NO_LOCK`, `LOCK_EXPIRED`, `LOCK_CONFLICT`, `AMBIGUOUS_LOCK`, `MULTI_ISSUE`
- `MISSING_REFS`, `FORBIDDEN_CLOSE_KEYWORD`, `MISMATCH_REFS`
- `ISSUE_NOT_FOUND`, `ISSUE_NOT_OPEN`

## docs_boundary_guard.sh
Hard gate для границы `docs/**`:
- блокирует только создание **новых** файлов в `docs/**` (status `A`);
- изменения существующих `docs/**` разрешены;
- owner override возможен только при `PUNCTB_DOCS_OWNER_APPROVED=YES` и флаге `--allow-owner-override`.

### Запуск
```bash
bash ops/gates/docs_boundary_guard.sh --staged --allow-owner-override
bash ops/gates/docs_boundary_guard.sh --range "origin/dev..HEAD" --allow-owner-override
```

## issue_commit.sh
Безопасный коммит целевых файлов в грязном дереве:
- принимает обязательный `--issue <id>`, `--message` и `--files`/`--file`;
- поддерживает два режима: обычный explicit issue-bound path и `--full` для полного pre-push-style gate-loop;
- проверяет issue (`gh issue view`, state=`OPEN`) и активные lock-конфликты для целевых файлов (`assert-issue-files`);
- нормализует только автоматические gate-event'ы через global `gatesctl approve`; human-only approvals остаются внешним evidence и не подставляются wrapper'ом автоматически;
- без `--full` запускает `docs_sync_gate.sh` только в advisory-режиме и не расширяет scope автоматически;
- `--full` включает blocking `docs_sync`; для auto-updated docs вне явного scope требуется `--expand-doc-targets`;
- для migration scope требует `--full` и запускает `dba_review_gate.sh`;
- `autoreview_gate.sh` на commit-time запускается только для risky/full scope (`web/**`, `backend/functions/**`, ops/hooks/templates/bin, release/main scope);
- `teamlead_orchestrator.sh --mode milestone` обязателен только для `--full` major/risky scope; при `retry_required=true` повторяет весь finish-loop до лимита `PUNCTB_FINISH_LOOP_MAX`;
- перед коммитом вызывает `gates_verify_commit.sh`, получает `receipt_id`/`policy_version` и валидирует machine-wide gates receipt;
- применяет docs-boundary guard к staged-файлам;
- дополнительно применяет branch-aware staged policy (`branch_policy_audit.py validate-staged`): работает только на `dev`, а `docs/release.md` разрешён только release issue с label `release`;
- стадирует только целевые пути (`git add -A -- <paths>`);
- формирует временный message-файл в `~/.codex/tmp/punctb` (с trace-header) и гарантирует `Refs #<id>` через `lock_issue_resolver.py ensure-message`;
- дописывает в commit message `Gate-Receipt: <receipt_id>` и `Gate-Policy: <policy_version>`;
- коммитит только целевые пути (`git commit --only -- <paths>`), не захватывая несвязанные staged изменения;
- после коммита вызывает `gates_bind_commit.sh` и делает immutable bind receipt -> `commit_sha`;
- после коммита выполняет пост-валидацию `verify-commit --check-gh --require-open`;
- после успешного коммита снимает lock только по коммитнутым путям текущей issue через `lock_release_by_issue.py` (fallback/idempotent поверх `post-commit` hook).

### Запуск
```bash
bash ops/issue/issue_commit.sh \
  --issue 1037 \
  --message "web: update profile toolbar" \
  --files "web/src/a.tsx,web/src/b.tsx"
```

### Gate order
1. `docs_sync_gate.sh` (`advisory` по умолчанию, `blocking` только для `--full`)
2. `dba_review_gate.sh` для migration scope (`--full` only)
3. `autoreview_gate.sh` только для risky/full scope
4. `teamlead_orchestrator.sh --mode milestone` только для major/risky/full scope
5. `gates_verify_commit.sh`
6. stage/commit/`gates_bind_commit.sh`/lock-release

## gates_verify_commit.sh
Thin wrapper над global `gatesctl verify --stage commit`:
- принимает `--issue`, `--files`/`--file` и `--repo-root`;
- вычисляет effective scope и policy из `docs/policy/gates.v1.yaml`;
- требует валидный `receipt_id` со статусом `ok`;
- возвращает JSON для `issue_commit.sh` с `receipt_id`, `policy_version`, `scope_fingerprint`.

### Запуск
```bash
bash ops/gates/gates_verify_commit.sh \
  --issue 1224 \
  --files "ops/issue/issue_commit.sh,docs/process/issue-commit-flow.md"
```

## gates_verify_push.sh
Thin wrapper над global `gatesctl audit-range`:
- принимает `--range` и optional `--target-branch`;
- для `dev/main` требует валидные bound receipts у всех новых коммитов диапазона;
- используется из `issue_audit_local.sh` и `git-hooks/pre-push` для обычного push-path;
- `issue:push:done` не подменяет этот wrapper для обычного push-path: вместо receipt-based range audit он завершает собственный branch-aware/risky strict gate и передаёт scoped approval artifact только на свой внутренний `git push`.

### Запуск
```bash
bash ops/gates/gates_verify_push.sh --range "@{upstream}..HEAD"
```

## gates_bind_commit.sh
Thin wrapper над global `gatesctl bind-commit`:
- принимает `--issue`, `--commit`, `--receipt` и optional `--repo-root`;
- связывает receipt с фактическим `commit_sha`;
- может использоваться повторно как idempotent/best-effort fallback из `git-hooks/post-commit`.

### Запуск
```bash
bash ops/gates/gates_bind_commit.sh \
  --issue 1224 \
  --commit HEAD \
  --receipt gr_v1_example1234
```

## docs_sync_gate.sh
Автосинхронизация internal docs после code/process changes:
- принимает issue-bound scope через `--files` или повторяющийся `--file`, удаляет дубли и вычисляет только существующие allowlist-targets: `README.md`, `web/README.md`, `backend/README.md`, `docs/process/scripts.md`, `docs/process/issue-commit-flow.md`;
- запрещает менять user-facing `docs/**`;
- если scope не попадает в поддерживаемые code/process зоны, не найден ни один target-документ, scope является pure process-only (`README.md`, `package.json`, `.gitignore`, `AGENTS.md`, `GEMINI.md`, `openspec/**`) или все вычисленные doc-targets уже явно входят в commit-scope, завершает gate успешным `SKIPPED`;
- в `advisory`-режиме не пишет файлы и не блокирует commit; используется для fast/обычного `issue:commit`;
- в `blocking`-режиме разрешён для `issue:commit --full`, `release:prepare` и `issue:push:done`;
- запускает reviewer-first цикл через `codex exec`: сначала read-only reviewer, затем writer-pass в workspace-write только при `verdict=request_changes`;
- ограничивает writer-pass и reviewer-pass встроенным file-context и возвращает JSON summary с `ok`, `reason`, `updated_files`, `scope_files`, `doc_targets`, `artifact_dir`.

### Запуск
```bash
DOCS_SYNC_MAX_ATTEMPTS=2 \
bash ops/gates/docs_sync_gate.sh --issue 1214 --file ops/gates/docs_sync_gate.sh
```

## dba_review_gate.sh
Dual DBA-review gate для migration scope:
- принимает только `backend/init/migrations/*` и `backend/init/migration_manifest.lock`;
- автоматически добавляет manifest в review-scope, если есть изменения миграций;
- выполняет `check_migration_layout.sh` и `check_migrations_consistency.sh`;
- запускает reviewer A/B в read-only и bounded auto-fix loop в workspace-write;
- возвращает JSON summary с `ok`, `reason`, `updated_files`, `dba_targets`, `artifact_dir`.

### Запуск
```bash
bash ops/db/dba_review_gate.sh --issue 1214 --file backend/init/migrations/20260310201500_client_home_public_surface.sql
```

## autoreview_gate.sh
Issue-bound pre-commit gate для non-migration scope:
- принимает `--issue`, `--files`/`--file` или `--range`, а также `--max-attempts` или `AUTOREVIEW_MAX_ATTEMPTS`;
- требует доступный `codex`, schema-файл `templates/autoreview.schema.json` и risk-matrix `templates/swarm-risk-matrix.yaml`;
- пишет артефакты в `~/.codex/tmp/punctb/autoreview/<issue>/<timestamp>/`, итоговый summary лежит в `final-gate.json`;
- сначала прогоняет matrix-derived conventional checks, затем независимые `reviewer_a` и `reviewer_b`, после каждого `request_changes` допускает bounded fixer-loop только внутри scope;
- для pure process/docs-only scope (`README.md`, `package.json`, `.gitignore`, `AGENTS.md`, `GEMINI.md`, `openspec/**`) после зелёных conventional checks завершает gate без LLM-review;
- основной commit-time caller (`issue_commit.sh`) не запускает gate для pure process/docs-only scope без `--full`; этот scope проверяется либо full-path, либо push-time через `issue:push:done`;
- для web scope запускает path-aware проверки: `npm --prefix web run check:test-imports`, scoped `eslint` по файлам scope и scoped `vitest` только по тест-файлам из scope;
- для process-contract scope выполняет локальный syntax-lint (`bash -n`, JSON parse), а неподдержанные non-web/non-agent checks помечает как `skipped`;
- если scope содержит `backend/init/migrations/**`, немедленно возвращает `HUMAN_GATE_REQUIRED` и не подменяет DBA gate.

### Причины завершения
- `OK` — все обязательные checks зелёные, reviewer A/B вернули `ok`;
- `CHECK_FAILED` — упал хотя бы один обязательный conventional check;
- `CHECK_UNAVAILABLE` — обязательный check нельзя выполнить в текущем окружении;
- `HUMAN_GATE_REQUIRED` — migration scope должен идти через DBA-gate, а не через autoreview;
- `REVIEWER_A_FAILED`, `REVIEWER_B_FAILED`, `REVIEWER_A_BLOCKED`, `REVIEWER_B_BLOCKED` — reviewer-pass завершился ошибкой или blocked verdict;
- `FIXER_AFTER_REVIEWER_A_FAILED`, `FIXER_AFTER_REVIEWER_B_FAILED` — fixer нарушил scope/упал после reviewer findings;
- `MAX_ATTEMPTS_EXCEEDED` — bounded fixer-loop не довёл scope до зелёного состояния за лимит попыток.

### Запуск
```bash
bash ops/gates/autoreview_gate.sh \
  --issue 1213 \
  --files "ops/gates/autoreview_gate.sh,docs/process/scripts.md"
```

## teamlead_orchestrator.sh
Teamlead-first orchestration для major change:
- классифицирует scope через `ops/teamlead/role_opinion_matrix.py` и расширенный `swarm-risk-matrix.yaml`;
- запускает независимые role-opinions (`frontend-role`, `frontend-design`, `backend-role`, `architect-role`, `dba-role`, `qa-role`, `devops-role`, `techwriter-role`) через `codex exec --ephemeral`;
- для pure process-scope (`README.md`, `package.json`, `.gitignore`, `AGENTS.md`, `GEMINI.md`, `openspec/**`) возвращает зелёный summary сразу после matrix-classification, не плодя nested role-runs поверх process-only diff;
- в `milestone` режиме допускает bounded main-session-style fixer loop внутри scope;
- в `finish` режиме работает read-only и используется как часть strict push-gate перед `issue:push:done`;
- возвращает JSON summary с `required_opinions`, `major_change`, `auto_commit_eligible`, `retry_required`, `owner_choice_required`, `artifact_dir`.

### Запуск
```bash
bash ops/teamlead/teamlead_orchestrator.sh --issue 1214 --mode milestone --file ops/issue/issue_commit.sh
```

## role_opinion_matrix.py
Helper для process-first классификации scope:
- читает расширенный `templates/swarm-risk-matrix.yaml`;
- вычисляет `highest_risk`, `required_checks`, `required_opinions`, `touched_domains`, `major_change`, `auto_commit_eligible`;
- автоматически добавляет `architect-role` для cross-domain/architecture/routing/critical scope.

### Запуск
```bash
python3 ops/teamlead/role_opinion_matrix.py \
  --matrix templates/swarm-risk-matrix.yaml \
  --files "web/src/app/router/AppRouter.tsx,backend/functions/main/index.ts"
```

## migration_apply_gate.sh
Guarded wrapper для реального применения миграций:
- принимает `--issue <id>` и migration-only scope;
- требует активный `lockctl` lease этой же issue на каждый файл migration scope, включая `backend/init/migration_manifest.lock`;
- перед apply всегда запускает `dba_review_gate.sh`;
- по умолчанию выполняет `bash backend/init/010_supabase_migrate.sh`, но через `-- <command>` можно передать другой devops apply-command;
- не встраивает `codex` в bootstrap-скрипт мигратора, а держит dual-DBA gate на orchestration-слое.

### Запуск
```bash
bash ops/db/migration_apply_gate.sh \
  --issue 1214 \
  --files "backend/init/migrations/20260310201500_client_home_public_surface.sql,backend/init/migration_manifest.lock"
```

## lock_release_by_issue.py
Точечное снятие `lockctl` locks по explicit issue и набору файлов:
- принимает `--issue-id` (числовой `GitHub issue id`) и `--files`/`--files-csv`/`--files-stdin`;
- читает активные locks issue через `lockctl status --issue`;
- снимает только активные locks issue по выбранным путям или целиком через `--drop-issue`;
- не трогает locks других issue.

### Запуск
```bash
python3 ops/issue/lock_release_by_issue.py --issue-id 1037 --files web/src/a.tsx web/src/b.tsx --json
python3 ops/issue/lock_release_by_issue.py --issue-id 1037 --drop-issue --json
```

## git-hooks/post-commit
Неблокирующая автоочистка lock сразу после каждого `git commit`:
- перед release lock делает best-effort `gates_bind_commit.sh` по `HEAD`;
- извлекает issue из `Refs #<id>` у `HEAD` через `lock_issue_resolver.py verify-commit --commit HEAD --json`;
- берёт список файлов `HEAD` и запускает `lock_release_by_issue.py` только для них;
- при невалидном/отсутствующем `Refs` печатает `LOCK_RELEASE_SKIP` и завершается с `0`;
- при ошибке очистки печатает `LOCK_RELEASE_WARN` и не ломает commit-flow.

## issue_done.sh
Явное закрытие issue по завершению:
- работает только на `dev`;
- проверяет, что issue открыта;
- проверяет отсутствие незапушенных коммитов с `Refs #<issue>`;
- по умолчанию требует bound `gatesctl` receipt у последнего issue-коммита;
- при вызове из `issue:push:done` принимает только scoped approval artifact той же issue/repo/branch/last_issue_commit и требует непустой `range` внутри артефакта;
- выполняет обязательную проверку и release активных `lockctl` locks по `issue_id = GitHub issue id`;
- закрывает issue через `gh issue close --comment`.

### Запуск
```bash
bash ops/issue/issue_done.sh --issue 1037
```

## issue_push_done.sh
Единая связка remote-завершения задачи:
- работает только на `dev`;
- прогоняет `issue_audit_local --skip-gates-audit --expected-issue <id>` для диапазона `@{upstream}..HEAD`;
- проверяет, что рабочее дерево чистое;
- проверяет, что issue `OPEN`;
- валидирует отсутствие active `lockctl`-конфликтов по файлам commit-range;
- прогоняет blocking `docs_sync_gate.sh` по range и блокирует push, если появились незакоммиченные doc-updates;
- для risky range запускает `autoreview_gate.sh`;
- запускает `teamlead_orchestrator.sh --mode finish`;
- проверяет acceptance checklist в issue (нет unchecked checkbox);
- требует, чтобы весь push-range состоял из commit'ов одной issue `Refs #<id>`;
- создаёт scoped approval artifact для конкретных `repo/branch/range/issue/last_issue_commit`;
- выполняет `git push` с этим scoped artifact, затем вызывает `issue_done.sh` с тем же scoped artifact.

### Запуск
```bash
bash ops/issue/issue_push_done.sh --issue 1037
```

### Параметры
- `--repo owner/repo` — явный репозиторий для `gh`.
- `--skip-acceptance-check` — явный bypass проверки acceptance.
- `--allow-no-checklist` — разрешить issue без checkbox-list.

## issue_audit_local.sh
Локальный wrapper для branch-aware аудита commit-range в `dev` (по умолчанию `@{upstream}..HEAD`):
- сначала запускает `branch_policy_audit.py audit-range`;
- по умолчанию затем вызывает `gates_verify_push.sh`, чтобы range без bound receipts не ушёл в push;
- опция `--expected-issue <id>` требует, чтобы все commit'ы диапазона ссылались на одну и ту же issue;
- флаг `--skip-gates-audit` оставляет только branch-aware audit и используется из `issue:push:done` перед созданием scoped approval artifact.

### Запуск
```bash
bash ops/issue/issue_audit_local.sh
bash ops/issue/issue_audit_local.sh --range "origin/dev..HEAD"
```

## branch_policy_audit.py
Branch-aware policy checks для `dev/main`:
- `validate-staged` — dev-only staged guard, включая правило для `docs/release.md`;
- `audit-range` — `dev` требует `OPEN` issue, `main` разрешает closed issues и проверяет release-label политику для `docs/release.md`;
- `assert-target` — проверка fast-forward topology и достижимости target SHA из `origin/dev` перед push в `main`.

### Запуск
```bash
python3 ops/issue/branch_policy_audit.py validate-staged --issue-id 1205
python3 ops/issue/branch_policy_audit.py audit-range --target-branch dev --range "origin/dev..HEAD"
python3 ops/issue/branch_policy_audit.py assert-target --target-branch main --local-sha <sha> --remote-sha <sha>
```

## release_prepare.sh
Release-only сборка `docs/release.md`:
- работает только на `dev` и только при clean tree;
- читает release issue с label `release`;
- собирает release notes из закрытых issues с label `release-note`;
- коммитит `docs/release.md` через `issue_commit.sh` под release issue.

### Запуск
```bash
bash ops/release/release_prepare.sh --issue 1205
```

## release_main.sh
Prod-like promotion `dev -> main`:
- требует `PUNCTB_MAIN_PUSH_APPROVED=YES`;
- работает только при clean tree;
- проверяет, что target SHA уже достижим из `origin/dev` и обновление `main` fast-forward;
- прогоняет docs boundary и branch-aware main audit;
- пушит только `git push origin <sha>:main` и затем закрывает release issue.

### Запуск
```bash
PUNCTB_MAIN_PUSH_APPROVED=YES bash ops/release/release_main.sh --issue 1205
```

## install_issue_hooks.sh
Устанавливает обязательные hooks и проверяет `gh auth`:
- `git config core.hooksPath git-hooks`
- проверяет, что `core.hooksPath` реально равен `git-hooks`;
- делает executable для `git-hooks/commit-msg`, `git-hooks/pre-push`, `git-hooks/post-commit`, `git-hooks/reference-transaction`.
- branch-creation guard в `git-hooks/reference-transaction` блокирует новые локальные ветки без owner override, но разрешает узкий bootstrap локальной `dev` только на актуальный tip `origin/dev`.

### Запуск
```bash
bash ops/issue/install_issue_hooks.sh
```

Подробный runbook процесса: `docs/process/issue-commit-flow.md`.
