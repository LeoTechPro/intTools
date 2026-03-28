# Релизлог

Этот файл фиксирует понятные записи по каждому локальному commit репозитория `/int/tools`. Запись готовится перед commit и входит в тот же commit.

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
