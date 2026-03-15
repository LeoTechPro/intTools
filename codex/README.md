# Codex Scripts

`codex/` хранит versioned host-tooling для Codex CLI и смежного MCP-окружения.
Канонические wrapper'ы и install/runbook-обвязка живут здесь; OpenClaw вынесен в `/git/openclaw`, а managed assets для `~/.codex` лежат в `assets/codex-home/`.

## Контракт

- Канонические Codex-facing wrapper'ы и install/ops-обвязка живут в `/git/scripts/codex`.
- Managed assets для `~/.codex` живут в `/git/scripts/codex/assets/codex-home/`.
- Project overlays для `~/.codex/projects/*` живут в `/git/scripts/codex/projects/` и синхронизируются в runtime автоматически.
- Runtime/log/tmp/state этого домена живут вне git, в `~/.codex`.
- Секретные env-файлы MCP живут не в `~/.codex/var`, а в `/git/.runtime/codex-secrets/`; legacy path поддерживается только как fallback.
- Любые cron/systemd записи должны ссылаться на файлы из этого каталога, а не на продуктовые репозитории.
- Канонический cron entrypoint для orphan cleaner: `/git/scripts/codex/cleanup_agent_orphans.sh`.
- `~/.codex/scripts/cleanup-agent-orphans.sh` допустим только как compatibility wrapper для старых вызовов.
- Для refresh managed assets в runtime используйте `/git/scripts/codex/sync_runtime_from_repo.sh`.
- Для окончательного отключения git в `~/.codex` используйте `/git/scripts/codex/detach_home_git.sh`.
- Для clean-room восстановления используйте `/git/scripts/codex/bin/codex-host-bootstrap`, `/git/scripts/codex/bin/codex-host-verify` и `/git/scripts/codex/bin/codex-recovery-bundle`.

## Канонические runtime-path

- логи: `~/.codex/log/`
- временные файлы: `~/.codex/tmp/`
- OpenClaw runtime: `/git/openclaw/`
- прочий Codex runtime/state: `~/.codex/`
- Codex MCP secrets runtime: `/git/.runtime/codex-secrets/`
- Cloud runtime: `/git/.runtime/cloud-access/`

## Текущие утилиты

- `duplex_bridge.py` — debate-bridge; по умолчанию пишет лог в `~/.codex/log/debate/duplex_bridge.log`
- `cleanup_agent_orphans.sh` — уборка осиротевших MCP/agent процессов
- `install_orphan_cleaner_cron.sh` — установка канонической cron-записи на `/git/scripts/codex/cleanup_agent_orphans.sh`
- `cloud_access.sh` — ленивый доступ к `gdrive`/`yadisk` через `rclone mount` и единый runtime `RCLONE_CONFIG=/git/.runtime/cloud-access/rclone.conf`
- `install_cloud_access.sh` — развёртывание runtime-каталогов `/git/.runtime/cloud-access`, mountpoints `/git/cloud/*` и user-level symlink units
- `bin/` — MCP entrypoints и прочие Codex-facing launcher'ы
- `tools/` — repo-managed helper trees (`mcp-obsidian-memory`, `obsidian-desktop`, `openspec`)
- `assets/codex-home/` — versioned `AGENTS.md`, `rules/`, `prompts/`, `skills/`, `version.json` для синхронизации в `~/.codex`
- `projects/` — tracked project-specific overlay-файлы для `~/.codex/projects/`
- `sync_runtime_from_repo.sh` — синхронизация managed assets из `assets/codex-home/` в `~/.codex`
- `detach_home_git.sh` — безопасное отключение git в `~/.codex` после подготовки `assets/codex-home/`
- `bin/codex-host-bootstrap` — bootstrap рабочего минимума Codex/OpenClaw/cloud tooling
- `bin/codex-host-verify` — проверка clean layout и целостности ссылок
- `bin/codex-recovery-bundle` — export/import шифрованного recovery-бандла с секретным runtime-слоем

## Recovery Layout

- `~/.codex` должен содержать только Codex-generated runtime/state и синхронизируемые managed-assets.
- Наши wrapper'ы, templates и policy остаются в `/git/scripts/codex`.
- Живые секреты для MCP храним в `/git/.runtime/codex-secrets/`.
- `OpenClaw` остаётся в `/git/openclaw`, а его секретный слой входит в recovery bundle.
- `sync_runtime_from_repo.sh` теперь синхронизирует не только `assets/codex-home`, но и tracked `projects/`.

### Базовая процедура восстановления

1. Установить `codex-cli`.
2. Восстановить секретный слой через `codex-recovery-bundle import`.
3. Запустить `/git/scripts/codex/bin/codex-host-bootstrap`.
4. При необходимости выполнить `codex login`.
5. Проверить контур через `/git/scripts/codex/bin/codex-host-verify` и `/git/openclaw/ops/verify.sh`.

## Cloud Access

- Канонические unit-файлы лежат в `/git/scripts/codex/systemd/` и подключаются в `~/.config/systemd/user/` через symlink.
- Исключение для этого контура согласовано отдельно: runtime mountpoints и `rclone` config живут внутри `/git`, а не в `~/.codex`, чтобы Codex/OpenClaw работали с облаками через уже разрешённый файловый корень.
- Основной runtime:
  - config: `/git/.runtime/cloud-access/rclone.conf`
  - cache: `/git/.runtime/cloud-access/cache`
  - logs: `/git/.runtime/cloud-access/log`
  - mounts: `/git/cloud/gdrive`, `/git/cloud/yadisk`
- После настройки remotes используйте:
  - `/git/scripts/codex/cloud_access.sh config`
  - `systemctl --user start rclone-mount-gdrive.service`
  - `systemctl --user start rclone-mount-yadisk.service`
