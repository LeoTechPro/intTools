# Релизлог

Этот файл фиксирует понятные записи по каждому локальному commit репозитория `/int/tools`. Запись готовится перед commit и входит в тот же commit.

## 2026-03-28
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
