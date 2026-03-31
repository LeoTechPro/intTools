# Релизлог

Этот файл фиксирует понятные записи по каждому локальному commit репозитория `/int/tools`. Запись готовится перед commit и входит в тот же commit.

## 2026-03-31
### review-fix: унифицирован launcher `lockctl-mcp.cmd` и исправлен Linux exec-bit
- В `lockctl/install_lockctl.sh` добавлены alias-линки `lockctl.cmd` и `lockctl-mcp.cmd` для Linux, чтобы Windows-style launcher имя было доступно кроссплатформенно.
- MCP-конфиги переведены на явный `lockctl-mcp.cmd`: `codex/templates/config.toml.tmpl`, `codex/plugins/lockctl/.mcp.json`, `codex/projects/punctb/.mcp.json`, `openclaw/.mcp.json`.
- В `codex/bin/codex-host-verify` добавлена совместимая проверка двух вариантов launcher (`lockctl-mcp` и `lockctl-mcp.cmd`), чтобы не ломать существующие runtime-конфиги.
- Для `codex/bin/mcp-lockctl.sh` и `openclaw/bin/mcp-lockctl.sh` выставлен executable mode (`100755`), чтобы Linux launcher можно было исполнять напрямую.

### review-fix: устранены cross-drive сбои `/int/...` на Windows для lockctl и интеграций
- В `gatesctl/gatesctl.py` и `punctb`-утилитах (`lock_issue_resolver.py`, `lock_release_by_issue.py`, `agent_lock_cleanup.py`) обновлён `LOCKCTL_BIN` resolver: `/int/...` корректно резолвится на фактический диск Windows.
- В `gatesctl/gatesctl.py` и `punctb`-утилитах добавлен py-launch fallback: если `LOCKCTL_BIN` указывает на `lockctl.py`, команда запускается через `sys.executable`, чтобы на Windows не возникал `WinError 193`.

### review-fix: точечные правки bootstrap/preflight по подтверждённым findings
- В `scripts/codex/codex_preflight.ps1` удалена принудительная перезапись process `PATH` (`User + Machine`): preflight больше не искажает фактический runtime-резолв бинарей в текущей сессии.
- В `scripts/codex/bootstrap_windows_toolchain.ps1` убран user-specific hardcode (`C:\\Users\\intData\\...`) и введены вычисления путей через `$env:LOCALAPPDATA`/`$PSScriptRoot`, чтобы скрипт был переносимым между профилями.
- В `bootstrap_windows_toolchain.ps1` добавлен reuse существующего portable CMake (`Resolve-PortableCMakeBin`) до сетевой установки, что устраняет повторную переустановку при повторном запуске.

### Windows Codex toolchain bootstrap + preflight
- Добавлены скрипты `scripts/codex/bootstrap_windows_toolchain.ps1` и `scripts/codex/codex_preflight.ps1` для воспроизводимой настройки Windows CLI-инструментов и быстрой диагностики статуса (`ok|missing|blocked|fix_suggested`, таблица/JSON).
- `bootstrap_windows_toolchain.ps1` фиксирует контракт exit-codes: `0` (готово), `10` (нужен elevated shell), `20` (частичные ошибки), пишет PATH snapshot/results в `/int/.tmp/toolchain-bootstrap/<UTC>/`.
- Реализована mixed-логика установки: `winget` для основного стека, `choco -> winget` fallback для `make`, portable fallback для `cmake`, alias fallback для `7z` через `M2Team.NanaZip` в user-scope.
- Реализована PATH-normalization: приоритет `WinGet\Links`/`WindowsApps`, очистка несуществующих user PATH entries, удаление stale `OpenAI\\Codex\\bin`.
- Обновлён `README.md` разделом полезных команд для bootstrap/preflight.

### lockctl installer: Windows PATH launcher delegation
- В `lockctl/install_lockctl.ps1` исправлен Windows installer: вместо копирования `.cmd` без соседних `.py` теперь генерируются delegating-launchers с абсолютным путём к исходным wrapper'ам в `/int/tools`.
- Installer выбирает install-dir с приоритетом PATH-aware (`%APPDATA%\npm`/`%USERPROFILE%\bin`) и при необходимости дописывает выбранный путь в user PATH.

### lockctl: кроссплатформенное ядро + MCP + adapters для Codex/OpenClaw
- `lockctl` переработан в модульное ядро `lockctl/lockctl_core.py` с сохранением CLI-контракта (`acquire|renew|release-path|release-issue|status|gc`) через совместимый entrypoint `lockctl/lockctl.py`.
- Добавлены Windows launcher'ы `lockctl/lockctl.ps1` и `lockctl/lockctl.cmd`, поддержан `python -m lockctl` через `lockctl/__main__.py`, обновлён POSIX wrapper `lockctl/lockctl`.
- Добавлен state resolver: `LOCKCTL_STATE_DIR` -> `$CODEX_HOME/memories/lockctl` -> platform default (`~/.codex/...`/`%USERPROFILE%\.codex\...`) и one-time Windows migration legacy state `D:\home\leon\.codex\memories\lockctl` с backup marker.
- Исправлена нормализация путей: корректная обработка Windows absolute-path в `--path` и хранение `path_rel` строго относительно `repo_root`.
- Добавлен MCP server `codex/bin/mcp-lockctl.py` + launcher'ы (`.sh`/`.cmd`) и OpenClaw adapters (`openclaw/bin/mcp-lockctl.sh`, `openclaw/bin/mcp-lockctl.cmd`, `openclaw/.mcp.json`).
- Обновлены интеграции `gatesctl` и `punctb` (`lock_issue_resolver.py`, `lock_release_by_issue.py`, `agent_lock_cleanup.py`) для Windows-style `LOCKCTL_BIN` path resolution.
- Обновлены runtime/config контракты: `codex/templates/config.toml.tmpl`, `codex/layout-policy.json`, `codex/bin/codex-host-verify`, `codex/projects/punctb/.mcp.json`, `codex/tools/install_tools.sh`.
- Добавлен skill `codex/assets/codex-home/skills/lockctl/SKILL.md`, plugin scaffold `codex/plugins/lockctl/.codex-plugin/plugin.json` и marketplace entry `.agents/plugins/marketplace.json`.
- Обновлена документация lockctl/openclaw/process: `README.md`, `codex/assets/codex-home/AGENTS.md`, `punctb/docs/process/issue-commit-flow.md`, `openclaw/docs/reinstall-and-restore.md`, `openclaw/docs/lockctl-mcp.md`.
- Добавлен unit test `lockctl/tests/test_lockctl_core.py` для path/state behavior.

## 2026-03-29
### ngt-memory moved to external reference mode
- `ngt-memory` удалён из индекса `/int/tools` как gitlink и больше не участвует в репозиторных change-цепочках этого контура.
- В `.gitignore` добавлен `ngt-memory/`, чтобы локальный reference clone не загрязнял статус `intTools`.
- В `README.md` добавлен явный external-reference статус с upstream-ссылкой `https://github.com/ngt-memory/ngt-memory`.

### ngt-memory gitlink updated in intTools
- В `ngt-memory` зафиксирован новый gitlink commit `34aa4e2cb6c8b57441549dd2c32748f0de4260ad` в составе дерева `/int/tools`.
- Обновление включает прокидку `OPENAI_BASE_URL` в API/session flow и поддержку `base_url` в `NGTMemoryLLMWrapper` для OpenAI-compatible провайдеров.

### intbrain-mcp: canonical PM tools surfaced in MCP wrapper
- В [codex/bin/mcp-intbrain.py](/int/tools/codex/bin/mcp-intbrain.py) добавлен полный canonical PM набор в `TOOLS`:
  - `intbrain_pm_dashboard`
  - `intbrain_pm_tasks`
  - `intbrain_pm_task_create`
  - `intbrain_pm_task_patch`
  - `intbrain_pm_para`
  - `intbrain_pm_health`
  - `intbrain_pm_constraints_validate`
  - `intbrain_import_vault_pm`
- В `_call_tool` добавлена маршрутизация на `pm/*` и `import/vault/pm` без изменения существующих tool names/контрактов.
- Для `intbrain_import_vault_pm` введён отдельный env-контур `INTBRAIN_CORE_ADMIN_TOKEN`:
  - при наличии токена отправляется `X-Core-Admin-Token`;
  - при отсутствии MCP возвращает локальную ошибку `config_error` без лишнего HTTP roundtrip.
- В [README.md](/int/tools/README.md) обновлён публичный список `intbrain-mcp` tools, добавлены требования по `INTBRAIN_CORE_ADMIN_TOKEN` и напоминание о перезапуске MCP runtime для refresh `tools/list`.

## 2026-03-28
### intbrain-mcp: people/group/jobs policy toolset expansion
- В [codex/bin/mcp-intbrain.py](/int/tools/codex/bin/mcp-intbrain.py) расширен универсальный MCP toolset новыми инструментами:
  - `intbrain_people_policy_tg_get`
  - `intbrain_group_policy_get`
  - `intbrain_group_policy_upsert`
  - `intbrain_jobs_list`
  - `intbrain_jobs_get`
  - `intbrain_job_policy_upsert`
  - `intbrain_jobs_sync_runtime`
  - `intbrain_policy_events_list`
- Обновлён роутинг MCP-адаптера на новые generic endpoints `groups/*`, `jobs/*`, `policies/events` без vendor-specific ветвлений.
- В [README.md](/int/tools/README.md) обновлён публичный список `intbrain-mcp` tools для OpenClaw/Codex и любых других agent profiles.

### Generic `intbrain-mcp` + OpenClaw thin adapter
- Добавлен универсальный MCP-адаптер `codex/bin/mcp-intbrain.py` и launcher `codex/bin/mcp-intbrain.sh` с единым toolset для memory-core `intbrain`.
- MCP toolset agent-agnostic: `intbrain_context_pack`, `intbrain_people_resolve`, `intbrain_people_get`, `intbrain_graph_neighbors`, `intbrain_context_store`, `intbrain_graph_link`.
- Добавлен `openclaw/bin/openclaw-intbrain-query.sh` как thin consumer-overlay: только трансляция в generic `/api/core/v1/context/pack` без OpenClaw-ветвлений в `intbrain`.
- Добавлен общий skill `codex/assets/codex-home/skills/intbrain-memory/SKILL.md` для DB-first retrieval/write-back по универсальному контракту.

### Canonical `.tmp` runtime-root для vault tooling
- `vault_sanitize.py` и `runtime_vault_gc.py` переведены на новый default runtime-root: `D:\int\.tmp\brain-runtime-vault` (VDS: `/int/.tmp/brain-runtime-vault`).
- В обоих скриптах добавлен единый override `--runtime-root`; при явном legacy path (`.../brain/runtime/vault`) выводится deprecation warning, но режим совместимости сохранён.
- `runtime_vault_gc.py` расширен: в `--apply` отдельно архивирует legacy path в `.tmp/<timestamp>/brain-runtime-vault-legacy` и очищает legacy-контур без удаления родительских `runtime/` каталогов.
- Обновлены `vault/installers/README.md` и корневой `README.md` с новым CLI-контрактом и примерами для local/VDS.

### Принят canonical vault tooling из `/int/brain`
- Добавлен новый machine-wide модуль `vault/installers/` с переносом installer-контента из `D:\int\brain\tools\vault\installers`.
- `vault_sanitize.py` переведён на canonical контур `/int/tools`: добавлены `--tools-root`, профили whitelist (`strict|balanced|permissive`, default `strict`) и legacy-алиас `--enforce-whitelist`.
- Добавлен `runtime_vault_gc.py` для архивирования и очистки `runtime/vault` с поддержкой `--dry-run`/`--apply`.
- Обновлён `vault/installers/README.md` под новый путь запуска и профильную политику.
- Корневой `README.md` обновлён: `vault/installers/` зафиксирован как canonical machine-wide tooling для vault cleanup.

## 2026-03-27
### Введена строгая env-политика и repo-guard
- В `.gitignore` добавлен единый блок `ENV POLICY (strict)`: в git разрешены только `*.env.example`/`*.example`, любые `*.env` и `config/runtime/*.env` игнорируются.
- В `.githooks/pre-push` добавлен `ENV POLICY GUARD`, который блокирует push, если в индекс попали запрещённые env-файлы.
- В `AGENTS.md` зафиксировано обязательное правило хранения runtime-секретов только вне git.

### Убраны non-example env из индекса
- `codex/debate.env` удалён из git-индекса (локальная копия оставлена в рабочем дереве как ignored).
- Изменение сделано без переписывания истории и без ротации секретов по отдельному указанию владельца.

## 2026-03-23
### Добавлен owner-gate на push в удалённый main
- В repo добавлен tracked `.githooks/pre-push`, который проверяет только target `refs/heads/main`: для такого push нужен `ALLOW_MAIN_PUSH=1`, а source branch должен быть локальной `main`.
- В `AGENTS.md`, `README.md` и `GEMINI.md` явно зафиксирован локальный bootstrap `git config core.hooksPath .githooks`, потому что tracked hook не активируется автоматически в новом checkout/worktree.

### В корневой README возвращён полный исторический контент
- В корневой `README.md` перенесено полное содержимое удалённых repo-owned вложенных `README.md` из предыдущего состояния репозитория, без сокращения технических деталей.
- Для каждого бывшего файла добавлен отдельный подраздел в блоке `Подкаталоги и локальные инструкции`, при этом сами вложенные `README.md` не возвращались.
- При переносе нормализованы только заголовки и ссылки, чтобы корневая документация сохранила полноту и не содержала битых переходов.

### README, AGENTS и RELEASE приведены к единому стандарту
- Корневой релизлог переименован в `RELEASE.md` и закреплён как единственный repo-local source-of-truth для релизлога.
- Корневой `README.md` оставлен единственной repo-owned документацией и инструкцией, а вложенные repo-owned `README.md` в active owner-зонах больше не используются.
- `AGENTS.md` теперь явно разводит роли `README.md`, `AGENTS.md` и `RELEASE.md`, а также требует обновлять `README.md` в том же commit, если меняется задокументированная поверхность.

### Codex-home больше не требует отдельного owner-approval на `git pull`
- В `codex/assets/codex-home/AGENTS.md` убрано требование спрашивать владельца перед обычным `git pull`.
- Ограничение на `git push` без ведома владельца сохранено.

### Pre-work sync стал auto-fast-forward шагом
- `AGENTS.md` теперь разрешает выполнять `git pull --ff-only` автоматически на чистой ветке с валидным upstream, без отдельного вопроса владельцу.
- Если дерево грязное, upstream отсутствует или `git pull --ff-only` не проходит, агент обязан остановиться и запросить дальнейшие действия с краткими вариантами решения.

### Инициализирован корневой релизлог
- В корне репозитория создан `RELEASE.md` как единый repo-local журнал изменений по локальным commit.
- `AGENTS.md` закрепляет обязательное обновление `RELEASE.md` перед каждым локальным commit.
- Альтернативные пути для релизлога, включая исторический `docs/`-путь, больше не считаются рабочими.
