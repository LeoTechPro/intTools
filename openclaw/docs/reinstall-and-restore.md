# OpenClaw reinstall and restore

Цель: восстановить локальный OpenClaw без зависимости от legacy in-tree runtime root.

## Канонический контракт

- binary: глобальный `openclaw`
- runtime home: `~/.openclaw`
- config: `~/.openclaw/openclaw.json`
- workspace: `~/.openclaw/workspace`
- mutable state: `~/.openclaw/*`
- versioned overlay: `/int/tools/openclaw`

## Что бэкапить перед reinstall

- `~/.openclaw/openclaw.json`
- `~/.openclaw/workspace/`
- `~/.openclaw/secrets/`
- runtime state:
  - `~/.openclaw/telegram/`
  - `~/.openclaw/credentials/`
  - `~/.openclaw/identity/`
  - `~/.openclaw/memory/`
  - остальные нужные state-подкаталоги

Бэкап не хранить в публичном git.

## Clean reinstall

```bash
npm install -g openclaw@latest
bash /int/tools/openclaw/ops/install.sh
```

## Restore

1. Остановить сервис: `systemctl --user stop openclaw-gateway.service`
2. Вернуть backup в `~/.openclaw/`
3. Убедиться, что пути в `~/.openclaw/openclaw.json` смотрят на:
   - `~/.openclaw/workspace`
   - `~/.openclaw/secrets/...`
   - `/int/tools/openclaw/bin/...` для helper wrapper'ов
4. Запустить сервис:
   - `systemctl --user daemon-reload`
   - `systemctl --user restart openclaw-gateway.service`
5. Проверить:
   - `bash /int/tools/openclaw/ops/verify.sh`
   - `openclaw gateway status`

## Критерий восстановления

После restore сервис должен запускаться и работать, даже если legacy in-tree runtime root отсутствует полностью.
