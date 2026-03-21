# Decommission audit: legacy in-tree OpenClaw runtime (2026-03-15)

## Фактчеки (активный runtime)

- `systemctl --user cat openclaw-gateway.service`:
  - `ExecStart` на `~/.local/lib/node_modules/openclaw/dist/index.js`, без in-tree `bin/openclaw`.
  - нет `OPENCLAW_GATEWAY_TOKEN`, нет in-tree `node_modules/openclaw`.
- `openclaw gateway status --json --no-probe`:
  - `.config.cli.path == /home/leon/.openclaw/openclaw.json`
  - `.config.daemon.path == /home/leon/.openclaw/openclaw.json`
  - `service.runtime.status == running`.
- `bash /int/tools/openclaw/ops/verify.sh`:
  - завершилось успешно (`openclaw verify: ok`).

## Аудит ссылок на legacy in-tree runtime в `/int`

Команда:

```bash
rg -n "legacy in-tree runtime|in-tree OpenClaw runtime" /int/README.md /int/tools \
  --glob '!**/node_modules/**' --glob '!**/.git/**' \
  --glob '!**/state/logs/**' --glob '!**/state/cron/**' --glob '!**/*.jsonl'
```

Результат: упоминания есть только в:

- `/int/README.md` — описания legacy/runtime-слоя и инвентаризации.
- `openclaw-concurrency-audit-2026-03-09.md` — исторический снапшот.
- `/int/tools/openclaw/docs/*` — документация decommission/restore.
- `/int/tools/openclaw/ops/verify.sh` — guard-проверки на отсутствие in-tree runtime path в service/status.

## Оценка

На момент аудита критичных runtime-ссылок на legacy in-tree runtime в активных контурах нет.  
Оставшиеся вхождения — исторические или целевые guard-проверки.

## Результат post-delete проверки

- Legacy in-tree runtime root уже отсутствует физически.
- `/int/.archive/openclaw-decommission-2026-03-15.tar.gz` создан.
- Архивы/исторические артефакты также сохранены в:
  - `/int/.archive/openclaw-systemd-legacy`
  - `/int/.archive/openclaw-workspace-git-20260315T091047Z`
- Ключевые active контуры не содержат runtime references на legacy in-tree runtime.
- Дополнительный smoke-этап:
  - `bash /int/tools/openclaw/ops/verify.sh` — проходит.
  - `bash /int/tools/codex/bin/codex-host-bootstrap --verify-only` — блокируется внешней инфраструктурной ошибкой mount `/int/cloud/yadisk`, не относящейся к decommission.

## Следующий шаг

- Отдельная задача: удалить удалённый репозиторий `LeoTechPro/openclaw` после ручного подтверждения владельца.
