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
- `vault/installers/` — канонический machine-wide vault tooling (`vault_sanitize.py`, `runtime_vault_gc.py`) для контуров `/2brain` + `/int/brain`;
- `intdb/` — self-contained operator CLI для remote Postgres/Supabase профилей, dump/restore и migration flow `/int/data`;
- `codex/` — versioned host-tooling, managed assets и project overlays для Codex CLI;
- `openclaw/` — versioned overlay для локального OpenClaw runtime;
- `data/` — внешний tooling/configs слой для backend-core `/int/data`;
- `probe/` — maintenance и audit-утилиты для `/int/probe`;
- `gemini-openai-proxy/` — internal-vendor copy локального OpenAI-compatible proxy для Gemini;
- `openspec/changes/` и `openspec/specs/` — proposal/spec материалы этого repo.

## Внешние референсы

- `ngt-memory` больше не ведётся как gitlink внутри `/int/tools`.
- Для изучения подходов agent-memory используем upstream-репозиторий `https://github.com/ngt-memory/ngt-memory` как внешний reference.

## OpenSpec governance

- Для любых tracked-мутаций repo-owned tooling в `/int/tools/**` канонический process source-of-truth живёт в `openspec/specs/process/spec.md`.
- Перед первой правкой обязателен owner-approved change package в `openspec/changes/<change-id>/`:
  - `proposal.md`
  - `tasks.md`
  - релевантный `spec.md` delta в `specs/**`
  - `design.md`, если меняется архитектура enforcement/runtime/resolver.
- `AGENTS.md`, `README.md` и managed governance docs в этом repo должны обновляться только вместе с соответствующим OpenSpec change, а не отдельно от него.

## Codex и OpenClaw

- runtime Codex живёт в `~/.codex`, а versioned overlay и bootstrap-утилиты — в `codex/`;
- self-authored/versioned Codex wrappers и publish/tooling живут только в `codex/`, в первую очередь в `codex/bin/`; `~/.codex` не используем как source-of-truth для таких скриптов;
- `codex/projects/` хранит tracked project overlays для runtime `~/.codex/projects/`;
- reusable browser tooling, Firefox MCP launcher-ы и profile-aware wrapper-скрипты живут только в `codex/bin/`;
- tracked Firefox MCP overlays для конкретных контуров живут только в `codex/projects/*/.mcp.json`;
- machine-readable routing registry для repo-owned high-risk capabilities живёт в `codex/config/agent-tool-routing.v1.json`, а resolver/validator CLI — в `codex/bin/agent_tool_routing.py`;
- canonical runtime layout dedicated Firefox MCP: `/int/.runtime/firefox-mcp/profiles/<profile>/`, `/int/.runtime/firefox-mcp/logs/<profile>/`, `/int/.runtime/firefox-mcp/run/<profile>.json`;
- `codex/tools/mcp-obsidian-memory/` содержит локальный MCP-сервер для vault `/2brain`;
- `codex/tools/obsidian-desktop/` хранит repo-managed launcher и desktop config для Obsidian;
- `codex/assets/codex-home/skills/javascript/` хранит repo-managed resources, scripts и templates для JavaScript skill assets;
- runtime OpenClaw живёт в `~/.openclaw`, а versioned overlay и runbooks — в `openclaw/`.
- На `vds.intdata.pro` canonical host-user split такой: IntData automation/deploy — `intdata`, Codex remote runtime — `agents`, OpenClaw runtime/service — `agents`; automation под `leon` для этого хоста не является допустимым default-path.

## Markdown context policy

- Каноническая политика сжатия markdown-контекста хранится в `data/markdown-context-policy.json`.
- Для `.md` индексаторов и RAG-проходов используем единый denylist-контур: `max_bytes`, `exclude_exact_paths`, `exclude_globs`.
- Политика по формулировкам `missing/not found/отсутствует`: оставляем только behavior-critical контекст (контракты API, коды ошибок, диагностические инциденты).

## Полезные команды

- `lockctl --help` — справка по file lease-локам;
- `gatesctl --help` — справка по gate receipts и commit binding;
- `python /int/tools/vault/installers/vault_sanitize.py --dry-run --profile strict` — dry-run санитарной миграции vault;
- `python /int/tools/vault/installers/runtime_vault_gc.py --dry-run --brain-root /int/brain` — dry-run архивации и очистки canonical runtime-root (`/int/.tmp/brain-runtime-vault`);
- `python /int/tools/vault/installers/runtime_vault_gc.py --dry-run --runtime-root /int/brain/runtime/vault` — compatibility-режим для legacy runtime-path (с deprecation warning);
- `python /int/tools/intdb/lib/intdb.py doctor --profile intdata-dev` — проверка native PostgreSQL CLI, TCP и SQL для локально настроенного DB profile;
- `python /int/tools/intdb/lib/intdb.py migrate status --target intdata-dev --repo /int/data` — сравнение remote `schema_migrations` и `migration_manifest.lock` из `/int/data`;
- `python /int/tools/delivery/bin/publish_repo.py --repo-path /int/data --repo-name data --success-label publish_data --expected-branch main --expected-upstream origin/main --push-remote origin --push-branch main --require-clean --deploy-mode ssh-fast-forward --deploy-host vds-intdata-intdata --deploy-repo-path /int/data --deploy-fetch-ref main --deploy-pull-ref main` — canonical publish engine для `/int/data`;
- `python /int/tools/delivery/bin/multica_autopilot_report_sidecar.py --target 6053a2d3-682f-48ca-a76a-ba1f09faa5e5=<master_issue_id> --dry-run` — dry-run доставки autopilot hygiene-отчёта в существующий Multica issue + Probe outbox; runtime mapping можно задавать через `AUTOPILOT_REPORT_TARGETS`;
- `pwsh -File /int/tools/codex/bin/publish_data.ps1` — compatibility wrapper поверх canonical publish engine для `/int/data`;
- В owner-facing командах `push/publish/выкатывай/публикуй` агент не вправе сам сокращать уже подготовленный состав publication: локальный commit по своему/scope допустим как обычно, но перед самой публикацией выборочно скрывать/откладывать "чужие" правки из publication-state запрещено.
- `ssh vds-intdata-intdata` — canonical remote shell для IntData deploy/apply/smoke на `vds.intdata.pro`;
- `ssh vds-intdata-agents` — canonical remote shell для Codex runtime на `vds.intdata.pro`;
- `ssh vds-intdata-agents` — canonical remote shell для OpenClaw runtime/service на `vds.intdata.pro`;
- `python -m unittest discover -s delivery/tests -p test_publish_repo.py -v` — hermetic regression smoke для canonical publish engine и PowerShell compatibility adapter: clean-tree guard, `-NoDeploy` publish, shared SSH resolver и `partial_state` на локально подменённом `ssh` без реальной сети;
- `/int/tools/codex/bin/mcp-intbrain.sh` и `D:\int\tools\codex\bin\mcp-intbrain.cmd` — запуск универсального MCP-адаптера `intbrain-mcp` (Phase 2, agent-agnostic);
- `/int/tools/openclaw/bin/openclaw-intbrain-query.sh --owner <id> "<query>"` — thin consumer-обёртка OpenClaw поверх generic `intbrain` API;
- `/int/tools/codex/bin/codex-host-bootstrap` — bootstrap рабочего минимума Codex/OpenClaw/cloud tooling;
- `pwsh -File /int/tools/scripts/codex/bootstrap_windows_toolchain.ps1 -AllowUserFallback` — idempotent bootstrap Windows CLI-toolchain (`rg`, `fd`, `yq`, `uv`, `pnpm`, `terraform`, `make`, PATH-normalization, fallback для `cmake/7z`);
- `pwsh -File /int/tools/scripts/codex/codex_preflight.ps1` — preflight-проверка ключевых CLI с machine-readable режимом `-Json`;
- `/int/tools/codex/bin/openspec` — tracked Linux entrypoint для локального OpenSpec CLI;
- `pwsh -File D:\int\tools\codex\bin\openspec.ps1` — tracked Windows PowerShell entrypoint для локального OpenSpec CLI;
- `D:\int\tools\codex\bin\openspec.cmd` — tracked Windows CMD entrypoint для локального OpenSpec CLI;
- `python /int/tools/scripts/codex/int_git_sync_gate.py --stage start` (Linux) или `python D:/int/tools/scripts/codex/int_git_sync_gate.py --stage start` (Windows) — обязательный start-gate для текущего checkout в `/int/*` (`clean check -> fetch -> pull --ff-only` только если `behind>0`);
- `python /int/tools/scripts/codex/int_git_sync_gate.py --stage finish --push` (Linux) или `python D:/int/tools/scripts/codex/int_git_sync_gate.py --stage finish --push` (Windows) — обязательный finish-gate для текущего checkout (`clean check -> fetch -> verify -> push -> post-push fetch`, без auto-merge/rebase);
- `python /int/tools/scripts/codex/int_git_sync_gate.py --stage start --all-repos --root-path /int` — явный legacy-style scan всех top-level repo, когда нужен массовый проход вместо default current-repo режима;
- `python /int/tools/codex/bin/agent_tool_routing.py validate --strict --json` — validate registry и blocker-rules для V1 high-risk tooling;
- `python /int/tools/codex/bin/agent_tool_routing.py resolve --intent publish:data --platform windows --json` — machine-readable resolution `logical intent -> canonical engine -> thin adapter`;
- `pwsh -File /int/tools/codex/bin/mcp-firefox-devtools.ps1 -ProfileKey firefox-default -StartUrl http://127.0.0.1:8080/ -DryRun` — dry-run канонического Firefox DevTools MCP launcher-а;
- `bash /int/tools/openclaw/ops/verify.sh` — проверка overlay OpenClaw;
- `AUTH_TYPE=oauth-personal HOST=127.0.0.1 PORT=11434 npm start` из `gemini-openai-proxy/` — локальный запуск proxy.

## Tailscale Private Admin Channel (v1)

- Tailscale используется как приватный ops/admin канал между `local PC`, `vds.intdata.pro` и `vds.punkt-b.pro`, а не как замена публичного ingress.
- Канонический runbook: `/int/tools/codex/docs/runbooks/tailscale-tailnet-v1.md`.
- Для `vds.intdata.pro` сохраняется разделение host-users: `intdata` (automation/deploy), `agents` (Codex/OpenClaw runtime/service).
- Для `prod` действует stricter policy: default-path только read-first и отдельный restricted SSH user; full root workflow не открывается автоматически.

### Tailnet-First SSH Transport (repo-managed)

- Канонический transport-слой для publish/deploy находится в:
  - `/int/tools/codex/bin/int_ssh_resolve.py`
  - `/int/tools/codex/bin/int_ssh_resolve.ps1`
  - `/int/tools/codex/bin/int_ssh_host.sh`
  - `/int/tools/codex/config/int_ssh_config`
- User-home `~/.ssh/config`/`C:\Users\intData\.ssh\config` этим rollout-ом не редактируется.
- Контракт режима:
  - `INT_SSH_MODE=auto|tailnet|public` (default `auto`)
  - `auto`: сначала tailnet probe, потом fallback в public с явным логом выбранного канала;
  - `tailnet`: только tailnet endpoint (без fallback);
  - `public`: только публичный endpoint.
- Контракт host-map/suffix:
  - `INT_SSH_TAILNET_SUFFIX`
  - `INT_SSH_DEV_PUBLIC_HOST`, `INT_SSH_PROD_PUBLIC_HOST`
  - `INT_SSH_DEV_TAILNET_NODE/HOST`, `INT_SSH_PROD_TAILNET_NODE/HOST`
- Короткий probe timeout: `INT_SSH_PROBE_TIMEOUT_SEC`.

## IntBrain Agent-Memory Integration

- `codex/plugins/intbrain/` публикует IntBrain как packaged Codex plugin в каталоге `IntData Tools`.
- `codex/bin/mcp-intbrain.py`, `codex/bin/mcp-intbrain.sh` и `codex/bin/mcp-intbrain.cmd` публикуют универсальный MCP toolset:
  - `intbrain_context_pack`
  - `intbrain_people_resolve`
  - `intbrain_people_get`
  - `intbrain_people_policy_tg_get`
  - `intbrain_group_policy_get`
  - `intbrain_group_policy_upsert`
  - `intbrain_graph_neighbors`
  - `intbrain_context_store`
  - `intbrain_graph_link`
  - `intbrain_jobs_list`
  - `intbrain_jobs_get`
  - `intbrain_job_policy_upsert`
  - `intbrain_jobs_sync_runtime`
  - `intbrain_policy_events_list`
  - `intbrain_pm_dashboard`
  - `intbrain_pm_tasks`
  - `intbrain_pm_task_create`
  - `intbrain_pm_task_patch`
  - `intbrain_pm_para`
  - `intbrain_pm_health`
  - `intbrain_pm_constraints_validate`
  - `intbrain_import_vault_pm`
- Auth задаётся через `INTBRAIN_AGENT_ID` и `INTBRAIN_AGENT_KEY` (env/secret file), без жёсткой привязки к конкретному агенту.
- Для `intbrain_import_vault_pm` дополнительно нужен `INTBRAIN_CORE_ADMIN_TOKEN`; без него MCP возвращает `config_error` до HTTP-вызова.
- После обновления `mcp-intbrain.py` требуется перезапуск Codex/OpenClaw (или MCP runtime), чтобы refresh `tools/list` подтянул новый PM toolset.
- OpenClaw и Codex используют один и тот же generic контракт; agent-specific UX остаётся только в overlay-скриптах `/int/tools/*`.

## Git Branch Policy

- для каждого checkout/worktree локально включаем `git config core.hooksPath .githooks`, чтобы активировать tracked guardrail из `.githooks/pre-push`;
- для multi-machine работы в `/int/*` обязателен двухфазный sync-gate: `int_git_sync_gate.py --stage start` до правок и `int_git_sync_gate.py --stage finish --push` перед закрытием задачи;
- tracked `.githooks/pre-push` дополнительно запускает `python -m unittest codex.tests.test_publish_repo -q` как smoke-gate только для push в `main`; non-main push этим smoke-path не блокируются;
- любой push в удалённый `main` требует явный `ALLOW_MAIN_PUSH=1` и допускается только из локальной `main`;
- push в `dev` и другие non-main branches этим repo-local guardrail не ограничивается.

## Подкаталоги и локальные инструкции

Ниже восстановлено содержимое удалённых repo-owned `README.md` из предыдущего состояния репозитория.

### `codex/`

#### Codex Scripts

`codex/` хранит versioned host-tooling для Codex CLI и смежного MCP-окружения.
Канонические wrapper'ы и install/runbook-обвязка живут здесь; live runtime OpenClaw вынесен в `~/.openclaw`, а versioned overlay лежит в `/int/tools/openclaw`. Managed assets для `~/.codex` лежат в `assets/codex-home/`.

##### Контракт

- Канонические Codex-facing wrapper'ы и install/ops-обвязка живут в `/int/tools/codex`.
- Managed assets для `~/.codex` живут в `/int/tools/codex/assets/codex-home/`.
- Project overlays для `~/.codex/projects/*` живут в `/int/tools/codex/projects/` и синхронизируются в runtime автоматически.
- Runtime/log/tmp/state этого домена живут вне git, в `~/.codex`.
- Секретные env-файлы MCP живут не в `~/.codex/var`, а в `/int/.runtime/codex-secrets/`; legacy path поддерживается только как fallback.
- Любые cron/systemd записи должны ссылаться на файлы из этого каталога, а не на продуктовые репозитории.
- Канонический cron entrypoint для orphan cleaner: `/int/tools/codex/cleanup_agent_orphans.sh`.
- `~/.codex/scripts/cleanup-agent-orphans.sh` допустим только как compatibility wrapper для старых вызовов.
- Для refresh managed assets в runtime используйте `/int/tools/codex/sync_runtime_from_repo.sh`.
- Для окончательного отключения git в `~/.codex` используйте `/int/tools/codex/detach_home_git.sh`.
- Для clean-room восстановления используйте `/int/tools/codex/bin/codex-host-bootstrap`, `/int/tools/codex/bin/codex-host-verify` и `/int/tools/codex/bin/codex-recovery-bundle`.

##### Канонические runtime-path

- логи: `~/.codex/log/`
- временные файлы: `~/.codex/tmp/`
- OpenClaw runtime: `~/.openclaw/`
- OpenClaw overlay/runbooks: `/int/tools/openclaw/`
- прочий Codex runtime/state: `~/.codex/`
- Codex MCP secrets runtime: `/int/.runtime/codex-secrets/`
- Cloud runtime: `/int/.runtime/cloud-access/`

##### Текущие утилиты

- `duplex_bridge.py` — debate-bridge; по умолчанию пишет лог в `~/.codex/log/debate/duplex_bridge.log`
- `cleanup_agent_orphans.sh` — уборка осиротевших MCP/agent процессов
- `install_orphan_cleaner_cron.sh` — установка канонической cron-записи на `/int/tools/codex/cleanup_agent_orphans.sh`
- `cloud_access.sh` — ленивый доступ к `gdrive`/`yadisk` через `rclone mount` и единый runtime `RCLONE_CONFIG=/int/.runtime/cloud-access/rclone.conf`
- `install_cloud_access.sh` — развёртывание runtime-каталогов `/int/.runtime/cloud-access`, mountpoints `/int/cloud/*` и user-level symlink units
- `bin/` — MCP entrypoints и прочие Codex-facing launcher'ы
- `bin/publish_*.ps1` — compatibility wrappers для контуров `/int/*`; canonical publish engine живёт в `/int/tools/delivery/bin/publish_repo.py`, а `codex/bin/*.ps1` не являются source-of-truth для publish-логики.
- `bin/agent_tool_routing.py` + `../config/agent-tool-routing.v1.json` — routing contract для repo-owned high-risk capabilities; blocked path не подменяется verified skill автоматически, fallback допустим только как explicit approved metadata.
- `tools/` — repo-managed helper trees (`mcp-obsidian-memory`, `obsidian-desktop`, `openspec`)
- `assets/codex-home/` — versioned `AGENTS.md`, `rules/`, `prompts/`, `skills/`, `version.json` для синхронизации в `~/.codex`
- `projects/` — tracked project-specific overlay-файлы для `~/.codex/projects/`
- `sync_runtime_from_repo.sh` — синхронизация managed assets из `assets/codex-home/` в `~/.codex`
- `detach_home_git.sh` — безопасное отключение git в `~/.codex` после подготовки `assets/codex-home/`
- `bin/codex-host-bootstrap` — bootstrap рабочего минимума Codex/OpenClaw/cloud tooling
- `bin/codex-host-verify` — проверка clean layout и целостности ссылок
- `bin/codex-recovery-bundle` — export/import шифрованного recovery-бандла с секретным runtime-слоем

##### Recovery Layout

- `~/.codex` должен содержать только Codex-generated runtime/state и синхронизируемые managed-assets.
- Наши wrapper'ы, templates и policy остаются в `/int/tools/codex`.
- Самописные publish/helper scripts для Codex не храним в `~/.codex/scripts`; home-контур допускается только для native tools и обязательных runtime instructions/compat wrappers, если их нельзя вынести из home-layout.
- Живые секреты для MCP храним в `/int/.runtime/codex-secrets/`.
- `OpenClaw` runtime живёт в `~/.openclaw`, а versioned overlay остаётся в `/int/tools/openclaw`.
- Секретный слой OpenClaw для recovery bundle берётся из `~/.openclaw/secrets/`.
- `sync_runtime_from_repo.sh` теперь синхронизирует не только `assets/codex-home`, но и tracked `projects/`.
- dedicated Firefox MCP runtime использует repo-managed launcher'ы и project overlays отсюда; owner browser profile не является source-of-truth для automated browser-proof.

###### Базовая процедура восстановления

1. Установить `codex-cli`.
2. Восстановить секретный слой через `codex-recovery-bundle import`.
3. Запустить `/int/tools/codex/bin/codex-host-bootstrap`.
4. При необходимости выполнить `codex login`.
5. Проверить контур через `/int/tools/codex/bin/codex-host-verify` и `/int/tools/openclaw/ops/verify.sh`.

##### Cloud Access

- Канонические unit-файлы лежат в `/int/tools/codex/systemd/` и подключаются в `~/.config/systemd/user/` через symlink.
- Исключение для этого контура согласовано отдельно: runtime mountpoints и `rclone` config живут внутри `/int`, а не в `~/.codex`, чтобы Codex/OpenClaw работали с облаками через уже разрешённый файловый корень.
- Основной runtime:
  - config: `/int/.runtime/cloud-access/rclone.conf`
  - cache: `/int/.runtime/cloud-access/cache`
  - logs: `/int/.runtime/cloud-access/log`
  - mounts: `/int/cloud/gdrive`, `/int/cloud/yadisk`
- После настройки remotes используйте:
  - `/int/tools/codex/cloud_access.sh config`
  - `systemctl --user start rclone-mount-gdrive.service`
  - `systemctl --user start rclone-mount-yadisk.service`

### `codex/assets/codex-home/skills/javascript/resources/`

#### Resources for javascript

### `codex/assets/codex-home/skills/javascript/scripts/`

#### Scripts for javascript

### `codex/assets/codex-home/skills/javascript/templates/`

#### Templates for javascript

### `codex/projects/`

#### Codex Project Overlays

Здесь лежат tracked project-specific overlay-файлы для Codex runtime.

Правила:
- этот каталог — канонический источник project overlays вместо ручных файлов в `~/.codex/projects/*`;
- синхронизация в runtime выполняется через `/int/tools/codex/sync_runtime_from_repo.sh`;
- в tracked overlay не храним секреты;
- реальные env-файлы живут в `/int/.runtime/codex-secrets/`.
- browser-proof overlays для dedicated Firefox MCP обязаны вызывать только repo-managed wrapper'ы из `/int/tools/codex/bin/**`, а не raw `npx`.

### `codex/tools/mcp-obsidian-memory/`

#### mcp-obsidian-memory

Локальный MCP сервер для vault `/2brain`.

Сервер работает с root-vault `2brain`; индекс OpenClaw при этом может использовать более узкий include-набор директорий, чтобы не тащить архивный и служебный шум в memory search.

##### Tools
- `vault_status`
- `list_notes`
- `read_note`
- `search_notes`
- `upsert_note`
- `move_note_para`
- `link_notes`
- `audit_links`
- `suggest_links`

##### Run

```bash
cd /int/tools/codex/tools/mcp-obsidian-memory
npm start
```

##### Smoke

```bash
node /int/tools/codex/tools/mcp-obsidian-memory/scripts/smoke-client.mjs
```

### `codex/tools/obsidian-desktop/`

#### Obsidian Desktop Config (Repo-managed)

Все канонические конфиги и инструкции для desktop-интеграции Obsidian хранятся в `/int/tools/codex/tools/obsidian-desktop`.
Они открывают root-vault агента `/2brain`.

##### Файлы
- `launcher.sh` — запуск Obsidian на vault `/2brain`
- `obsidian-memory.desktop` — desktop entry
- `obsidian.json` — канонический список vault-ов
- `install.sh` — ставит симлинки в `~/.local` и `~/.config`

Этот helper остаётся owner-manual exception и не входит в automation/runtime migration для `vds.intdata.pro`.

##### Применение
```bash
bash /int/tools/codex/tools/obsidian-desktop/install.sh
```

После запуска:
- `~/.local/bin/obsidian -> /int/tools/codex/tools/obsidian-desktop/launcher.sh`
- `~/.local/share/applications/obsidian-memory.desktop -> /int/tools/codex/tools/obsidian-desktop/obsidian-memory.desktop`
- `~/.config/obsidian/obsidian.json -> /int/tools/codex/tools/obsidian-desktop/obsidian.json`

Это гарантирует, что конфиги и launcher'ы не зависят от `~/.codex/tools`.

### `intdb/`

#### intdb

`/int/tools/intdb` — self-contained operator CLI для remote Postgres/Supabase профилей с этой машины.

##### Контракт

- tracked bootstrap живёт рядом с инструментом: `README.md`, `AGENTS.md`, `.env.example`, launchers и tests;
- локальный `.env` допустим только как untracked runtime-файл рядом с инструментом;
- временные dump/log/CSV-артефакты живут только в ignored путях `.tmp/` и `logs/`;
- `INTDB_DATA_REPO` может задаваться как через process env, так и через локальный `intdb/.env`; типовые runtime-ошибки должны выходить как обычные `intdb:` сообщения без traceback;
- native migration-path тоже должен быть самодостаточным: `bootstrap` использует тот же profile-password, а `incremental` при необходимости сам прокидывает найденный PostgreSQL `bin` в `PATH` дочернего `bash`;
- для `/int/data` tool не дублирует schema ownership и migration engine, а переиспользует owner flow через `init/010_supabase_migrate.sh`, `init/schema.sql` и `migration_manifest.lock`.

##### Основные команды

- `doctor` — проверка native PostgreSQL CLI, TCP и SQL для профиля;
- `sql` / `file` — ad-hoc SQL и SQL-файлы, по умолчанию в read-only режиме;
- `dump` / `restore` / `clone` / `copy` — перенос данных между профилями через локальную машину;
- `migrate status` / `migrate data` — remote-операции для migration flow `/int/data`.

##### Safety

- mutating-команды требуют `--approve-target <profile>`;
- для `WRITE_CLASS=prod` дополнительно обязателен `--force-prod-write`;
- thin wrappers в `codex/bin/intdb.*` только проксируют вызов в `/int/tools/intdb`.

### `data/`

#### data tooling

`/int/tools/data` — внешний ops/process/tooling contour для `data backend-core`.

##### Что живёт здесь

- host-level configs и proxy/systemd templates, которые больше не считаются частью product repo `/int/data`
- devops/docops/dev helpers для `data`
- cross-repo and machine-wide scripts, которые обслуживают `data` как платформенный backend

##### Что не живёт здесь

- canonical schema/functions/contracts backend-core
- runtime-state и секреты
- исходники отдельных сервисов `chat`, `bot`, `itsm`, `erp`

##### Структура

- `configs/` — host-level configs и templates
- `devops/` — ops helpers
- `devs/` — developer helpers
- `docops/` — docs/process helpers

`/int/data` остаётся owner только backend-core. Всё, что является внешним tooling или host-config слоем, должно жить здесь.

### `data/configs/`

#### intdata host configs

Этот каталог хранит внешний host-config слой для `intdata` и соседних family-сервисов.

##### Что находится здесь

- apache/nginx/systemd/fail2ban/docker helper configs
- generated vhost templates и ops reference files

##### Что не находится здесь

- canonical backend migrations/contracts/functions
- runtime-state и живые секреты

Если конфиг обслуживает хост, reverse proxy, systemd или внешний rollout path, его место здесь, а не в `/int/data`.

### `data/configs/nginx/`

#### Конфигурации nginx (reverse proxy перед Apache)

Каталог содержит итоговые конфиги `nginx`, сформированные на основе действующих `apache2` vhost'ов.
Исключение: [`api.intdata.pro.conf`](/int/tools/data/configs/nginx/api.intdata.pro.conf) ведётся отдельно как host-level custom vhost для Supabase API и не генерируется из Apache.

###### Назначение

- nginx принимает внешние HTTP/HTTPS-подключения (80/443), выполняет TLS-терминацию, безопасные заголовки и лимиты.
- Apache остаётся backend-сервером и слушает только на `127.0.0.1:8080` / `127.0.0.1:8443`.
- Конфиги генерируются скриптом `scripts/devops/generate_nginx_from_apache.py`, который подтягивает `ServerName`, `ServerAlias`, TLS-сертификаты и формирует пару `server {}` блоков (HTTP/HTTPS) для каждого vhost'а.

###### Процесс обновления

1. Убедитесь, что `/etc/apache2/sites-available/` содержит актуальные конфиги.
2. Запустите генератор из корня репозитория:
   ```bash
   python3 scripts/devops/generate_nginx_from_apache.py
   ```
   Файлы появятся в `configs/nginx/generated/`.
3. Примените конфиги на хосте:
   ```bash
    sudo cp configs/nginx/generated/*.conf /etc/nginx/sites-available/
    sudo ln -sf /etc/nginx/sites-available/<vhost>.conf /etc/nginx/sites-enabled/<vhost>.conf
    sudo nginx -t
    sudo systemctl reload nginx
   ```
4. После выпуска/продления сертификатов `certbot` необходимо выполнить `systemctl reload nginx`.

###### Дополнительно

- Общие сниппеты (`/etc/nginx/snippets/ssl-params.conf`) должны содержать жёсткие TLS-настройки и заголовки безопасности.
- Временное использование портов и сервисов фиксируйте в issue/worklog и сопровождайте machine-wide `lockctl` lease по изменяемым файлам. При оффлайне допускается запись в `AGENTS/issues.json` (`offline_queue`); после синхронизации с GitHub удалите черновик и отметьте время `Synced on <UTC>`. Постоянные изменения инфраструктуры отражайте в паспорте объектов `AGENTS/object_passport.yaml`.

###### Перевыпуск сертификатов через snap `certbot`

1. Убедитесь, что установлен snap-пакет:
   ```bash
   sudo snap install core; sudo snap refresh core
   sudo snap install --classic certbot
   sudo ln -sf /snap/bin/certbot /usr/bin/certbot
   ```
2. Для каждого нового домена пропишите webroot (см. конфиги — `/var/www/<domain>`):
   ```bash
   sudo mkdir -p /var/www/bot.intdata.pro
   sudo mkdir -p /var/www/id.intdata.pro
   sudo mkdir -p /var/www/id.intdata.pro
   sudo mkdir -p /var/www/nexus.intdata.pro
   sudo mkdir -p /var/www/sso.intdata.pro
   ```
3. Выпустите сертификаты (пример для одного домена, перечислите нужные `-d`; переменная `CERTBOT_EMAIL` обязательна). Проще всего использовать автоматизированный скрипт:
   ```bash
   export CERTBOT_EMAIL=ops@intdata.pro
   sudo scripts/devops/issue_intdata_certs.sh
   ```
   Либо вызвать вручную:
   ```bash
   sudo certbot certonly --webroot -w /var/www/bot.intdata.pro -d bot.intdata.pro
   sudo certbot certonly --webroot -w /var/www/id.intdata.pro -d id.intdata.pro
   sudo certbot certonly --webroot -w /var/www/id.intdata.pro -d id.intdata.pro
   sudo certbot certonly --webroot -w /var/www/nexus.intdata.pro -d nexus.intdata.pro
   sudo certbot certonly --webroot -w /var/www/sso.intdata.pro -d sso.intdata.pro
   ```
4. После успешного выпуска перезагрузите nginx:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

При необходимости можно объединять несколько доменов в один сертификат (`-d` через пробел), однако удобно поддерживать отдельные связки, чтобы разграничить сроки продления.

### `data/configs/systemd/`

#### configs/systemd

Шаблоны systemd-юнитов и вспомогательные обёртки. См. раздел `data/configs/` ниже и [AGENTS.md](/int/tools/data/AGENTS.md#configs) за регламент.

##### Новые юниты
- `meta-intdata-mailpit-dev.service` — orchestrator для docker-compose Mailpit (QA SMTP/UI).

### `data/devops/`

#### [scripts/devops](/int/tools/data/scripts/devops)

Скрипты DevOps-цикла (rebuild, restart, smoke) и инфраструктурные инструменты. Общие принципы описаны в разделах `data/` и `data/devops/` ниже.

- **configure_erp_sso.sh** — настраивает Keycloak-провайдеры для Odoo/ERPNext. Требует заполненного `erp/.env` и запущенных контейнеров (`docker compose -f erp/docker-compose.yaml up -d`).

##### Keycloak + Kill Bill (IAM биллинг/подписки)

- **/int/id/docker-compose.yaml** с профилем `keycloak` — standalone стек Keycloak + Kill Bill + Kaui + PostgreSQL.
- **setup_keycloak_killbill.sh** — управляющий скрипт (`start|stop|restart|logs|down|status`), принимает `--env` для указания файла переменных, проверяет обязательные секреты и автоматически бутстрапит Realm/тенант после запуска.
- Дополнительные флаги: `--clear-theme-cache` (очищает `kc-gzip-cache` в контейнере Keycloak после `up/restart`) и `--selenium-smoke` (запускает `scripts/devops/run_selenium_smoke.sh` для браузерного smoke).
- **killbill.overrides/killbill.properties.example** — пример overrides для Kill Bill (скопируйте в `killbill.properties` и подставьте секреты).
- **/int/id/scripts/devops/run_selenium_smoke.sh** — опциональный Selenium UI smoke для standalone repo Identity; выполняется только если selenium tests добавлены локально.

###### Быстрый старт

```bash
#### 1. Подготовьте env-файл (.env.dev) и заполните обязательные переменные:
####    ID_KEYCLOAK_DB_NAME, ID_KEYCLOAK_DB_USER, ID_KEYCLOAK_DB_PASSWORD,
####    ID_KEYCLOAK_ADMIN, ID_KEYCLOAK_ADMIN_PASSWORD,
####    ID_KEYCLOAK_ADMIN_CLIENT_ID, ID_KEYCLOAK_ADMIN_CLIENT_SECRET,
####    ID_KEYCLOAK_LOGIN_THEME (по умолчанию intdata),
####    ID_KEYCLOAK_DISPLAY_NAME (по умолчанию "intData SSO"),
####    ID_KEYCLOAK_DISPLAY_NAME_HTML (по умолчанию "intData SSO"),
####    ID_KILLBILL_DB_NAME, ID_KILLBILL_DB_USER, ID_KILLBILL_DB_PASSWORD,
####    ID_KILLBILL_ADMIN_USER, ID_KILLBILL_ADMIN_PASSWORD,
####    ID_KILLBILL_DEFAULT_API_KEY, ID_KILLBILL_DEFAULT_API_SECRET,
####    ID_KILLBILL_WEBHOOK_SECRET
####    ID_KEYCLOAK_REALM (опционально, по умолчанию intdata)
####    ID_KILLBILL_TENANT_NAME (опционально, по умолчанию "IntData Dev")
####    SSO клиенты модулей (см. id/.env.example):
####      BRAIN_SSO_*/BRAIN_ADMIN_SSO_*/BRAIN_API_SSO_*
####      CRM_SSO_*/CRM_ADMIN_SSO_*/CRM_API_SSO_*
#####      NEXUS_SSO_*/NEXUS_ADMIN_SSO_*/NEXUS_API_SSO_*
####      SUITE_SSO_*/SUITE_ADMIN_SSO_*/SUITE_API_SSO_*
####      ID_ADMIN_SSO_*, ID_API_SSO_*
####      BOT_ADMIN_SSO_*, BOT_API_SSO_*
####    (redirect/web_origins задаются CSV, по умолчанию используются dev-домены и localhost-порты)
#
#### 2. (опционально) Скопируйте killbill.overrides/killbill.properties.example в
####    killbill.overrides/killbill.properties и обновите значения.
#
#### 3. Запустите стек:
/int/id/scripts/devops/setup_keycloak_killbill.sh start --env /int/id/.env
#### при изменении тем Keycloak добавьте --clear-theme-cache, чтобы сбросить кеш статических ресурсов
#### для end-to-end smoke можно дополнительно указать --selenium-smoke
#### при старте выполняются проверки env и bootstrap Keycloak/Kill Bill (можно отключить, установив ID_BOOTSTRAP_DISABLED=1)

#### 4. Проверить состояние:
/int/id/scripts/devops/setup_keycloak_killbill.sh status

#### 5. Логи конкретного сервиса:
/int/id/scripts/devops/setup_keycloak_killbill.sh logs keycloak
```

> **Примечание:** `docker compose down` удаляет контейнеры/volume’ы; используйте опцию `down` скрипта только при необходимости.
>
> При bootstrap Keycloak создаётся (или обновляется) realm `intdata`, а также полный набор OIDC-клиентов для модулей платформы (`<module>-web`, `<module>-admin`, `<module>-api`). Конфигурация (client id, redirect-uri, web origins, client secret) считывается из переменных `*_SSO_*`/`*_ADMIN_SSO_*`/`*_API_SSO_*`. Значения по умолчанию ориентированы на домены `*.intdata.pro` и локальные порты; перед запуском продакшн-стека обязательно синхронизируйте их через OpenBao.
>
> Сессия bootstrap также применяет тему `ID_KEYCLOAK_LOGIN_THEME` и отображаемое имя Realm (`ID_KEYCLOAK_DISPLAY_NAME`, `ID_KEYCLOAK_DISPLAY_NAME_HTML`). Для брендовой темы `intdata` убедитесь, что в репозитории обновлены файлы `id/keycloak/themes/intdata`, затем выполните `restart` + `logs` + smoke.

###### Selenium UI smoke (standalone)

- Скрипт `scripts/devops/run_selenium_smoke.sh` выполняет headless smoke веб-интерфейсов (маркер `selenium`):
  1. создаёт/переиспользует виртуальное окружение `venv/`;
  2. устанавливает зависимости из `tests/requirements.txt`;
  3. запускает `pytest -m selenium tests/web/test_ui_selenium_smoke.py`, передавая дополнительные аргументы pytest из командной строки.
- Параметры через переменные окружения:
  - `CHROME_BINARY` — путь к Chromium/Chrome (по умолчанию `/usr/bin/chromium`);
  - `SELENIUM_URL_<MODULE>` — переопределённые хосты для smoke;
  - `SELENIUM_WAIT_TIMEOUT` — таймаут ожидания (секунды, дефолт 20).
- Примеры:

  ```bash
  /int/id/scripts/devops/run_selenium_smoke.sh -q
  CHROME_BINARY=/opt/google/chrome/chrome /int/id/scripts/devops/run_selenium_smoke.sh --maxfail=1
  ```

- Скриншоты и другие артефакты сохраняются в `tests/web/screenshots/`; не коммитим чувствительные данные.
- Флаг `setup_keycloak_killbill.sh --selenium-smoke` вызывает этот скрипт автоматически в конце DevOps-цикла.

###### Что делает стек

- **Keycloak** на `https://localhost:${ID_KEYCLOAK_HTTP_PORT:-8443}` — единый IdP для /id.
- **Kill Bill** на `http://localhost:${ID_KILLBILL_HTTP_PORT:-8081}` — биллинг/подписки.
- **KAUI** (админ Kill Bill) на `http://localhost:${ID_KAUI_HTTP_PORT:-9091}` — опционально (profile `kaui`).

###### DevOps задачи

- Создать секреты в vault/1Password (настоящие пароли не коммитить).
- Подготовить инфраструктурные БД (prod/stage) через команды DBA.
- Настроить systemd unit или orchestrator (k8s) на базе compose-файла.
- Добавить health-check в `scripts/devops/smoke.sh` после интеграции с /id.
- После обновления smoke (`scripts/devops/smoke.sh`) будет проверять Keycloak (`/.well-known/openid-configuration`) и Kill Bill (`/1.0/healthcheck`). Убедитесь, что переменные `ID_KEYCLOAK_HTTP_PORT_LEGACY`, `ID_KEYCLOAK_REALM`, `ID_KILLBILL_HTTP_PORT` заданы при запуске.

##### Mailpit (единый SMTP шлюз)

- **/int/id/docker-compose.yaml** с профилем `mailpit` — standalone манифест SMTP/UI сервиса (`mail.intdata.pro`, `smtp.intdata.pro`).
```
docker compose -f /int/id/docker-compose.yaml --profile mailpit ps
```
- **run-mailpit.sh** — zero-wait цикл (`rebuild → restart → logs → log-scan → smoke`), готовит каталоги и проверяет API `/api/v1/info` через `mail.intdata.pro`.
- **meta-intdata-mailpit-dev.service** — systemd-юнит (см. `configs/systemd/`) для автономного рестарта.

###### Быстрый старт

```bash
#### 1. Создайте директории и секреты:
####    sudo mkdir -p /var/lib/intdata/mailpit /etc/intdata/mailpit/tls /var/log/intdata/mailpit
####    sudo htpasswd -bc /etc/intdata/mailpit/users.htpasswd intdata-smtp '<smtp-password>'
####    sudo htpasswd -bc /etc/intdata/mailpit/ui.htpasswd intdata-ui '<ui-password>'
####    # TLS сертификаты mail.intdata.pro / smtp.intdata.pro поместите в /etc/intdata/mailpit/tls/
#
#### 2. Экспортируйте переменные (или заполните .env):
export SMTP_PASSWORD='<smtp-password>'
export MAILPIT_SMTP_USER='intdata-smtp'
export MAILPIT_UI_USER='intdata-ui'
export MAILPIT_DATA_DIR='/var/lib/intdata/mailpit'
export MAILPIT_CONFIG_DIR='/etc/intdata/mailpit'
export MAILPIT_LOG_DIR='/var/log/intdata/mailpit'

#### 3. Запустите цикл:
scripts/devops/run-mailpit.sh

#### 4. Убедитесь, что mailpit работает:
docker compose -f id/docker-compose.yaml --profile mailpit ps
```

> **Важно:** файлы `users.htpasswd`, `ui.htpasswd`, TLS-ключи и пароли не попадают в git. Управляйте ими через секрет-хранилище Владельца.

###### Сертификаты mail.intdata.pro / smtp.intdata.pro
- Фронт: `nginx` (80/443) → `apache2` (8080/8443) → `mailpit`.
- Сертификат Let's Encrypt выпускаем через snap `certbot`:

```bash
sudo certbot certonly \
  --webroot -w /var/www/letsencrypt \
  --cert-name mail.intdata.pro \
  -d mail.intdata.pro -d smtp.intdata.pro \
  --agree-tos --no-eff-email -m prointdata@ya.ru
```

- Симлинки в `/etc/intdata/mailpit/tls/` должны указывать на `/etc/letsencrypt/live/mail.intdata.pro-0001/{fullchain,privkey}.pem` для UI и SMTP (`mail.*`, `smtp.*`).
- После выпуска выполните `systemctl reload nginx apache2` и `scripts/devops/run-mailpit.sh` для обновления контейнера.

###### SMTP (Яндекс Почта)
- Проектные сервисы отправляют письма через `smtp.yandex.ru` (порт `465`, SSL), аккаунт `prointdata@yandex.ru`, пароль приложения задаёт владелец.
- Минимальные переменные `.env`: `SMTP_HOST=smtp.yandex.ru`, `SMTP_PORT=465`, `SMTP_USE_SSL=true`, `SMTP_USER=prointdata@yandex.ru`, `SMTP_PASSWORD=<yandex_app_password>`, `EMAIL_FROM=prointdata@yandex.ru`.
- Smoke-проверка отправки:

```bash
python - <<'PY'
import smtplib, ssl
from email.message import EmailMessage
msg = EmailMessage()
msg['Subject'] = 'Yandex SMTP smoke'
msg['From'] = 'prointdata@yandex.ru'
msg['To'] = 'prointdata@yandex.ru'
msg.set_content('Smoke delivery через smtp.yandex.ru')
context = ssl.create_default_context()
with smtplib.SMTP_SSL('smtp.yandex.ru', 465, context=context, timeout=15) as smtp:
    smtp.login('prointdata@yandex.ru', '<yandex_app_password>')
    smtp.send_message(msg)
print('sent')
PY
```

- Mailpit (`https://mail.intdata.pro`) используется только для QA/наблюдения; реальные письма уходят напрямую через Яндекс. Пароль приложения держим в секрет‑хранилище владельца, а в `.env` подставляем при деплое.

###### OpenBao (self-host)
- Конфиг объединён в `id/docker-compose.yaml` (profile `openbao`); переменные читаются из корневого `.env` (`OPENBAO_*`). Отдельный `.env.infisical УДАЛЁН` больше не используется.
- Запуск/перезапуск:

```bash
OPENBAO_ENV_FILE=.env \
scripts/devops/run-openbao.sh
```

- После старта выполните `python -m id.api.cli sync-openbao --env-file .env`, чтобы выгрузить секреты модулей в OpenBao и обновить секцию `OPENBAO SYNC` в `.env`.
- Проверка доступности:

```bash
```

- Root token (`ID_OPENBAO_TOKEN`) хранится только во внешнем секрет-хранилище. При ротации токена сначала обновите `.env`, затем повторно выполните `sync-openbao`.

##### Утилиты и вспомогательные скрипты

- **check_duplicates.py** — ищет дубликаты файлов по SHA-1. По умолчанию сканирует `/int/brain/web/static/diagnostics`, игнорируя `.git`, `node_modules`, build-артефакты. Код возврата `0`, если дублей нет, и `1`, если найдены совпадения. Пример:\
  `python3 scripts/devops/check_duplicates.py shared/assets -e build -e cache`.

- **dev-redeploy.sh** — стандартный DevOps-цикл для ветки `dev`: подтягивает `.env`, запускает rebuild/restart сервисов, собирает логи в `logs/devops/<UTC>/`, прогоняет `log-scan.py`, выполняет HTTP-smoke и дополнительно запускает [`smoke.sh`](/int/tools/data/devops/smoke.sh) (включая OpenBao). Использование:\
  `scripts/devops/dev-redeploy.sh`.

- **generate_nginx_from_apache.py** — миграционная утилита: читает активные Apache vhost’ы и генерирует эквивалентные прокси-конфиги nginx (HTTP+HTTPS) в `configs/nginx/generated/`. Требует root-доступ. Запуск:\
  `sudo python3 scripts/devops/generate_nginx_from_apache.py`.

- **import_archive_to_project.py** — импортирует оффлайн-черновики из `AGENTS/issues.json` (`offline_queue`) в GitHub Project V2: создаёт Draft Issue, переносит статус и основные поля (Status/Role/Module/Type) и очищает запись в зеркале. Нужен `GITHUB_TOKEN` (или `gh auth token`). Пример:\
  `python3 scripts/devops/import_archive_to_project.py --project-number 1`.

- **install_services.sh** — устанавливает/обновляет systemd unit’ы из `configs/systemd/` (копирование в `/etc/systemd/system`, `daemon-reload`, `enable`). Запуск только от root:\
  `sudo scripts/devops/install_services.sh`.

- **local-redeploy.sh** — локальный перезапуск dev-стека без полного DevOps-цикла: обновляет зависимости, кэширует фронт, перезапускает docker-compose сервисы. Применяется во время разработки:\
  `scripts/devops/local-redeploy.sh`.

- **log-scan.py** — ищет критические записи в логах (паттерн `ERROR|FATAL|CRITICAL|Traceback|...`). Используется внутри `dev-redeploy.sh`, но может запускаться отдельно:\
  `python3 scripts/devops/log-scan.py logs/devops/<timestamp>`.

- **project_deadline_guardian.py** — контролирует дедлайны карточек GitHub Project: переводит просроченные элементы в статус `Expired` и уведомляет указанных пользователей (см. workflow `project_deadline_guardian.yml`).

- **rebuild_service.sh** — точечный пересбор docker-compose сервиса: вызовет `docker compose build <service>` + `up -d`. Указываем compose-name из корневого `docker-compose.yml`:\
  `scripts/devops/rebuild_service.sh nexus-web`.

- **rebuild_smart_sidebar.sh** — пересборка фронтенда Nexus из canonical repo `/int/brain/web`, затем синхронизация артефактов в target web-root. Использование:\
  `scripts/devops/rebuild_smart_sidebar.sh`.

- **run_task_reminder_worker.py** — entrypoint для фонового воркера напоминаний (используется в systemd/cron). Интервал опроса берёт из `TASK_REMINDER_INTERVAL` (секунды). Запуск:\
  `python3 scripts/devops/run_task_reminder_worker.py`.

- **sync_discussions_mirror.py** — выгружает GitHub Discussions по категориям в JSON (например, `AGENTS/announcements.json`, `AGENTS/research.json`). По умолчанию берёт только активные обсуждения; флаг `--include-closed` добавляет закрытые. Примеры:\
  `python3 scripts/devops/sync_discussions_mirror.py --slug announcements --output AGENTS/announcements.json`\
  `python3 scripts/devops/sync_discussions_mirror.py --slug research --output AGENTS/research.json --include-closed`.

- **run-openbao.sh**, **run-mailpit.sh**, **run_selenium_smoke.sh**, **setup_keycloak_killbill.sh**, **smoke.sh** — описаны в разделах выше (OpenBao, Mailpit, Selenium smoke, IAM стек, DevOps smoke).

### `gatesctl/`

#### gatesctl

`gatesctl` — machine-wide runtime для gate receipts, approvals и commit binding поверх issue-bound процесса.

##### Shell UX

Используйте публичную точку входа:

```bash
gatesctl
gatesctl --help
gatesctl help verify
```

##### Runtime model

- Runtime truth хранится в SQLite, не в проектных YAML/JSON ledgers.
- GitHub Issue остаётся источником human context/evidence, но normalized state хранится в `gatesctl`.
- `lockctl` отвечает только за file lease и не хранит review/gate историю.
- Bound receipts не удаляются `gc`; очищается только sync-cache и старые unbound записи.

Runtime files:

- `GATESCTL_STATE_DIR` (если явно задан)
- иначе `~/.codex/memories/gatesctl`
- SQLite: `<state_dir>/gates.sqlite`
- Event log: `<state_dir>/events.jsonl`

##### Common examples

```bash
gatesctl plan-scope \
  --repo-root /int/crm \
  --issue 1224 \
  --files .agents/scripts/issue_commit.sh

gatesctl approve \
  --repo-root /int/crm \
  --issue 1224 \
  --gate docs-sync \
  --decision approve \
  --actor gatesctl \
  --role system \
  --files .agents/scripts/issue_commit.sh

gatesctl verify \
  --repo-root /int/crm \
  --issue 1224 \
  --stage commit \
  --files .agents/scripts/issue_commit.sh \
  --sync-issue

gatesctl bind-commit \
  --repo-root /int/crm \
  --commit-sha HEAD

gatesctl audit-range \
  --repo-root /int/crm \
  --target-branch dev \
  --range '@{upstream}..HEAD'
```

##### Notes

- Не редактируйте SQLite и `events.jsonl` напрямую.
- Repo-specific правила задаются policy-файлом, обычно `.agents/policy/gates.v1.yaml`.
- Для self-hosted remote можно использовать sample hook: `hooks/pre-receive.sample`.

##### Server-side hook

Sample `pre-receive` hook ожидает:

- bare/self-hosted remote, где доступен `gatesctl`;
- `GATESCTL_REPO_ROOT` — рабочий клон/checkout репозитория с policy-файлом;
- `GATESCTL_TARGET_BRANCH` при необходимости фиксированной ветки.

На GitHub.com такой hook не устанавливается; там этот sample служит только шаблоном для собственного central remote.

### `gemini-openai-proxy/`

#### Gemini ↔ OpenAI Proxy

Этот каталог теперь живёт внутри `/int/tools` как internal-vendor copy, а не как
самостоятельный git-репозиторий. Источник происхождения:
`https://inthub.com/Brioch/gemini-openai-proxy` (MIT License, см. `LICENSE`).

Что это означает на практике:

- upstream reference фиксируется в этом README, а не через `origin` в отдельном checkout;
- в `tools` храним только versioned исходники и документацию;
- `.git`, `node_modules/`, `dist/` и прочий runtime/build слой сюда не переносим;
- все локальные доработки дальше ведём уже как часть `LeoTechPro/intTools`.

Локальный OpenAI-compatible proxy для Gemini с опорой на current
`@google/gemini-cli`/`@google/gemini-cli-core` и существующую OAuth-сессию в
`~/.gemini`.

Целевой режим этого репозитория сейчас один:

- ручной запуск;
- только `127.0.0.1`;
- `AUTH_TYPE=oauth-personal`;
- совместимость с chat-completions клиентами уровня Cline/OpenWebUI/curl;
- поддержка text, stream, vision и tool calling.

##### Требования

- Node.js 24+;
- валидная локальная Gemini OAuth-сессия, обычно файл
  `~/.gemini/oauth_creds.json`;
- установленный доступ к Gemini через Google account.

##### Установка

```bash
npm install
```

##### Поддержанный запуск

```bash
AUTH_TYPE=oauth-personal \
HOST=127.0.0.1 \
PORT=11434 \
MODEL=gemini-3-flash-preview \
MODEL_FALLBACK_CHAIN=gemini-2.5-pro,gemini-2.5-flash,gemini-2.5-flash-lite \
npm start
```

Переменные окружения:

- `HOST` — по умолчанию `127.0.0.1`
- `PORT` — по умолчанию `11434`
- `AUTH_TYPE` — по умолчанию `oauth-personal`
- `MODEL` — primary model, по умолчанию `gemini-3-flash-preview`
- `MODEL_FALLBACK_CHAIN` — CSV-цепочка фолбэка, по умолчанию `gemini-2.5-pro,gemini-2.5-flash,gemini-2.5-flash-lite`

Текущая policy этого прокси:

- primary request model: `gemini-3-flash-preview`
- fallback chain: `gemini-2.5-pro -> gemini-2.5-flash -> gemini-2.5-flash-lite`
- если клиент передаёт `body.model`, прокси сначала пробует именно его, затем идёт по configured chain
- фолбэк срабатывает только на ошибки доступности модели: quota/capacity/429/not found

Проверка на этом хосте показала, что `auto`, `auto-gemini-2.5`, `pro`, `flash`
и `flash-lite` для `AUTH_TYPE=oauth-personal` использовать как model id не стоит.

Прокси на этом этапе не предназначен для внешней сети. Если нужен внешний
доступ, это отдельная задача с bind/reverse-proxy/auth/hardening.

##### Endpoints

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`

##### Быстрые проверки

Проверка здоровья:

```bash
curl http://127.0.0.1:11434/healthz
```

Простой chat completion:

```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [
      {"role": "user", "content": "Hello Gemini"}
    ]
  }'
```

Stream:

```bash
curl -N -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Say hello in one short sentence"}
    ]
  }'
```

Tool calling roundtrip:

```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [
      {"role": "user", "content": "What is the weather in Paris?"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "Get weather by city",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {"type": "string"}
            },
            "required": ["city"]
          }
        }
      }
    ]
  }'
```

Следующий ход после получения `tool_calls`:

```json
{
  "model": "gemini-3-flash-preview",
  "messages": [
    {"role": "user", "content": "What is the weather in Paris?"},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_123",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"city\":\"Paris\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_123",
      "content": "{\"temperature\":18,\"conditions\":\"Cloudy\"}"
    }
  ]
}
```

##### Как работает фолбэк

Для каждого запроса прокси собирает chain:

1. `body.model`, если клиент его передал
2. primary model из `MODEL`
3. модели из `MODEL_FALLBACK_CHAIN`

Дубликаты убираются. При ошибках вида quota/capacity/not found прокси
моментально пробует следующую модель. В успешном ответе поле `model`
содержит фактически использованную модель.

### `lockctl/`

#### lockctl

`lockctl` is the machine-local writer-lock runtime for Codex/OpenClaw on this host.

##### Shell UX

Use the public shell entrypoint from `PATH`:

```bash
lockctl
lockctl --help
lockctl help acquire
man lockctl
```

Bare `lockctl` prints the top-level help and exits successfully.

Install launchers into user bin:

```bash
bash /int/tools/lockctl/install_lockctl.sh
pwsh -File D:\int\tools\lockctl\install_lockctl.ps1
```

Implementation/core lives in `/int/tools/lockctl/lockctl_core.py`.
CLI entrypoints:

- Linux/macOS wrapper: `/int/tools/lockctl/lockctl`
- Python CLI: `/int/tools/lockctl/lockctl.py`
- Windows wrappers: `/int/tools/lockctl/lockctl.ps1`, `/int/tools/lockctl/lockctl.cmd`
- MCP entrypoint: `/int/tools/codex/bin/mcp-lockctl.py`

Do not try to execute the directory `/int/tools/lockctl` itself as a binary.

##### Runtime model

- One active writer lease per repo-relative file.
- Truth for active locks lives in SQLite, not in project-local YAML files.
- Leases are short-lived and must be renewed while a write is active.
- `release-path` is the normal per-file cleanup path.
- `release-issue` is the normal bulk cleanup path for issue-bound repos.

Runtime files:

- `LOCKCTL_STATE_DIR` (если явно задан)
- иначе `$CODEX_HOME/memories/lockctl`
- иначе platform default:
  - Linux: `~/.codex/memories/lockctl`
  - Windows: `%USERPROFILE%\.codex\memories\lockctl`
- SQLite: `<state_dir>/locks.sqlite`
- Event log: `<state_dir>/events.jsonl`

Windows migration note:

- При обнаружении legacy state `D:\home\leon\.codex\memories\lockctl` выполняется one-time migration в canonical `%USERPROFILE%\.codex\memories\lockctl` с backup и marker-файлом `.legacy-migration-v1.done`.

##### Common examples

```bash
lockctl acquire \
  --repo-root /int/crm \
  --path README.md \
  --owner codex:session-1 \
  --issue 1217 \
  --lease-sec 60 \
  --format json

lockctl status --repo-root /int/crm --issue 1217 --format json

lockctl release-path \
  --repo-root /int/crm \
  --path README.md \
  --owner codex:session-1 \
  --format json

lockctl release-issue --repo-root /int/crm --issue 1217 --format json

lockctl gc --format json
```

##### Notes

- Do not edit SQLite or `events.jsonl` directly.
- Active `/int/*` repos now treat `lockctl` as the runtime source of truth for active file locks.

### `openclaw/`

#### openclaw tools overlay

`/int/tools/openclaw` — versioned overlay для локального OpenClaw.

Legacy in-tree runtime root decommissioned и больше не является runtime-источником; исторические артефакты сохранены в отчётах decommission.

Канонический runtime теперь должен жить вне git:

- binary: `openclaw` из глобального install (`npm/pnpm/bun`)
- home/state: `~/.openclaw`
- config: `~/.openclaw/openclaw.json`
- workspace: `~/.openclaw/workspace`

Этот каталог хранит только versioned tooling:

- `bin/` — helper wrapper'ы для доменных запросов;
- `ops/` — install/verify/restart helper'ы вокруг official install;
- `systemd/` — versioned drop-in templates;
- `docs/` — runbook'и и исторические audit-артефакты по migration/decommission.

Инварианты:

- `node_modules/`, `state/`, `workspace/`, `secrets/` и live `openclaw.json` не хранятся в git;
- `openclaw gateway install --force` остаётся базовым способом переустановки user service;
- versioned файлы не должны содержать live token, секреты каналов или machine-specific runtime state.
- на этой машине OpenClaw требует Node 22.12+; overlay-скрипты по умолчанию подхватывают `$HOME/.nvm/versions/node/v24.8.0/bin`, если он установлен.

Быстрые команды:

```bash
bash /int/tools/openclaw/ops/install.sh
bash /int/tools/openclaw/ops/verify.sh
```

Основной runbook:

- [reinstall-and-restore.md](/int/tools/openclaw/docs/reinstall-and-restore.md)
- [openclaw-concurrency-audit-2026-03-09.md](/int/tools/openclaw/docs/openclaw-concurrency-audit-2026-03-09.md)
- [decommission-openclaw-2026-03-15.md](/int/tools/openclaw/reports/decommission-openclaw-2026-03-15.md)

### `openspec/changes/`

#### OpenSpec Changes

Active owner-approved change packages хранятся в подкаталогах `openspec/changes/*`.
Для tracked tooling/process mutations execution без active change package запрещён.

### `openspec/specs/`

#### OpenSpec Specifications

Текущие capability/process specs этого репозитория хранятся в подкаталогах `openspec/specs/*`.
Для tooling-governance канонический spec живёт в `openspec/specs/process/spec.md`; по умолчанию расширяем существующие capability specs и не создаём дубли без явного одобрения владельца.

### `probe/`

#### Probe Scripts

`probe/` хранит versioned maintenance и audit-утилиты для `Probe Monitor`, которые не входят в prod-core репозиторий `/int/probe`.

##### Контракт

- `/int/probe` содержит только код, deploy-конфиг и проверки.
- Versioned maintenance scripts и исторические audit snapshots для `Probe Monitor` живут здесь.
- Mutable state и runtime-data самого `Probe Monitor` живут вне git: `~/.local/state/probe-monitor` и `~/.local/share/probe-monitor`.
- Migration/cutover идёт через `/int/probe/ops/migrate_runtime.sh`, затем `ops/cutover.sh --install-units --restart-services` и `ops/verify.sh --runtime`.

##### Состав

- `collect_audit.sh` — сбор audit snapshot по текущему checkout `/int/probe`
- `docs/critical_assets.txt` — список must-survive assets и внешних runtime-path
- `docs/machine-audit-2026-03-02.md` — исторический audit snapshot, перенесённый из `probe`

