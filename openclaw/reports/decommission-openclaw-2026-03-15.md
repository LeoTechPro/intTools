# Decommission audit: `/git/openclaw` (2026-03-15)

## Фактчеки (активный runtime)

- `systemctl --user cat openclaw-gateway.service`:
  - `ExecStart` на `~/.local/lib/node_modules/openclaw/dist/index.js`, без `bin/openclaw` из `/git/openclaw`.
  - нет `OPENCLAW_GATEWAY_TOKEN`, нет `node_modules/openclaw` из `/git/openclaw`.
- `openclaw gateway status --json --no-probe`:
  - `.config.cli.path == /home/leon/.openclaw/openclaw.json`
  - `.config.daemon.path == /home/leon/.openclaw/openclaw.json`
  - `service.runtime.status == running`.
- `bash /git/tools/openclaw/ops/verify.sh`:
  - завершилось успешно (`openclaw verify: ok`).

## Аудит ссылок на `/git/openclaw` в `/git`

Команда:

```bash
rg -n "/git/openclaw" /git/README.md /git/tools /git/openclaw \
  --glob '!**/node_modules/**' --glob '!**/.git/**' \
  --glob '!**/state/logs/**' --glob '!**/state/cron/**' --glob '!**/*.jsonl'
```

Результат: ссылки есть только в:

- `/git/README.md` — описания legacy/runtime-слоя и инвентаризации.
- `/git/openclaw/README.md` — явное предупреждение что это legacy.
- `openclaw-concurrency-audit-2026-03-09.md` — исторический снапшот.
- `/git/tools/openclaw/docs/*` — документация decommission/restore (`Historical snapshot`, "без `/git/openclaw`").
- `/git/tools/openclaw/ops/verify.sh` — явные проверки на отсутствие легаси-путей в service/status.

## Оценка

На момент аудита критичных runtime-ссылок на `/git/openclaw` в активных контуров нет.  
Оставшиеся вхождения — исторические или целевые guard-проверки.

## Результат post-delete проверки

- `/git/openclaw` уже отсутствует физически.
- `/git/.archive/openclaw-decommission-2026-03-15.tar.gz` создан.
- Архивы/исторические артефакты также сохранены в:
  - `/git/.archive/openclaw-systemd-legacy`
  - `/git/.archive/openclaw-workspace-git-20260315T091047Z`
- Ключевые active контуры не содержат runtime references на `/git/openclaw`.
- Дополнительный smoke-этап:
  - `bash /git/tools/openclaw/ops/verify.sh` — проходит.
  - `bash /git/tools/codex/bin/codex-host-bootstrap --verify-only` — блокируется внешней инфраструктурной ошибкой mount `/git/cloud/yadisk`, не относящейся к decommission.

## Следующий шаг

- Отдельная задача: удалить удалённый репозиторий `LeoTechPro/openclaw` после ручного подтверждения владельца.
