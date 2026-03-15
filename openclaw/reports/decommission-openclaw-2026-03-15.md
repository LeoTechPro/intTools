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

## Что нужно сделать перед фактическим `rm -rf /git/openclaw`

1. Принять решение по архиву `.openclaw` исторических артефактов (`runtime/logs`, `workspace`, `state`) в `/git/openclaw`:
   - переместить в `/git/.archive/openclaw-*` или явно пометить как исторические;
   - зафиксировать, что recovery/bootstrap их больше не использует.
2. Сделать dry-run backup целевого дерева.
3. Запросить подтверждение на удаление GitHub-репозитория `LeoTechPro/openclaw`.

## Следующий шаг

- После подтверждения выполнить инвентарный backup:
  - `tar -czf /git/.archive/openclaw-decommission-2026-03-15.tar.gz /git/openclaw`
- Сделать `rm -rf /git/openclaw` только после ручного green-light.
