# Codex Scripts

`codex/` хранит versioned host-tooling для Codex/OpenClaw и смежного MCP-окружения.

## Контракт

- Исходники и инструкции живут в `/git/scripts/codex`.
- Runtime/log/tmp/state этого домена живут вне git, в `~/.codex`.
- Любые cron/systemd записи должны ссылаться на файлы из этого каталога, а не на продуктовые репозитории.
- Канонический cron entrypoint для orphan cleaner: `/git/scripts/codex/cleanup_agent_orphans.sh`.
- `~/.codex/scripts/cleanup-agent-orphans.sh` допустим только как compatibility wrapper для старых вызовов.

## Канонические runtime-path

- логи: `~/.codex/log/`
- временные файлы: `~/.codex/tmp/`
- инструменты и runtime: `~/.codex/tools/`

## Текущие утилиты

- `duplex_bridge.py` — debate-bridge; по умолчанию пишет лог в `~/.codex/log/debate/duplex_bridge.log`
- `cleanup_agent_orphans.sh` — уборка осиротевших MCP/agent процессов
- `install_orphan_cleaner_cron.sh` — установка канонической cron-записи на `/git/scripts/codex/cleanup_agent_orphans.sh`
