# Decommission audit: legacy in-tree OpenClaw runtime (2026-03-15)

## Фактчеки (активный runtime)

- `systemctl --user cat openclaw-gateway.service`:
  - `ExecStart` на `~/.local/lib/node_modules/openclaw/dist/index.js`, без in-tree `bin/openclaw`.
  - нет `OPENCLAW_GATEWAY_TOKEN`, нет in-tree `node_modules/openclaw`.
- `openclaw gateway status --json --no-probe`:
  - `.config.cli.path == /home/leon/.openclaw/openclaw.json`
  - `.config.daemon.path == /home/leon/.openclaw/openclaw.json`
  - `service.runtime.status == running`.
- `bash /git/tools/openclaw/ops/verify.sh`:
  - завершилось успешно (`openclaw verify: ok`).

## Аудит ссылок на legacy in-tree runtime в `/git`

Команда:

```bash
rg -n "legacy in-tree runtime|in-tree OpenClaw runtime" /git/README.md /git/tools \
  --glob '!**/node_modules/**' --glob '!**/.git/**' \
  --glob '!**/state/logs/**' --glob '!**/state/cron/**' --glob '!**/*.jsonl'
```

Результат: упоминания есть только в:

- `/git/README.md` — описания legacy/runtime-слоя и инвентаризации.
- `openclaw-concurrency-audit-2026-03-09.md` — исторический снапшот.
- `/git/tools/openclaw/docs/*` — документация decommission/restore.
- `/git/tools/openclaw/ops/verify.sh` — guard-проверки на отсутствие in-tree runtime path в service/status.

## Оценка

На момент аудита критичных runtime-ссылок на legacy in-tree runtime в активных контурах нет.  
Оставшиеся вхождения — исторические или целевые guard-проверки.

## Результат post-delete проверки

- Legacy in-tree runtime root уже отсутствует физически.
- `/git/.archive/openclaw-decommission-2026-03-15.tar.gz` создан.
- Архивы/исторические артефакты также сохранены в:
  - `/git/.archive/openclaw-systemd-legacy`
  - `/git/.archive/openclaw-workspace-git-20260315T091047Z`
- Ключевые active контуры не содержат runtime references на legacy in-tree runtime.
- Дополнительный smoke-этап:
  - `bash /git/tools/openclaw/ops/verify.sh` — проходит.
  - `bash /git/tools/codex/bin/codex-host-bootstrap --verify-only` — блокируется внешней инфраструктурной ошибкой mount `/git/cloud/yadisk`, не относящейся к decommission.

## Следующий шаг

- Отдельная задача: удалить удалённый репозиторий `LeoTechPro/openclaw` после ручного подтверждения владельца.
