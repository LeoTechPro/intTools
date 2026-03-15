# openclaw tools overlay

`/git/tools/openclaw` — versioned overlay для локального OpenClaw.

Канонический runtime теперь должен жить вне git:

- binary: `openclaw` из глобального install (`npm/pnpm/bun`)
- home/state: `~/.openclaw`
- config: `~/.openclaw/openclaw.json`
- workspace: `~/.openclaw/workspace`

Этот каталог хранит только versioned tooling:

- `bin/` — helper wrapper'ы для доменных запросов;
- `ops/` — install/verify/restart helper'ы вокруг official install;
- `systemd/` — versioned drop-in templates;
- `docs/` — runbook'и и исторические audit-артефакты по migration/decommission.

Инварианты:

- `node_modules/`, `state/`, `workspace/`, `secrets/` и live `openclaw.json` не хранятся в git;
- `openclaw gateway install --force` остаётся базовым способом переустановки user service;
- versioned файлы не должны содержать live token, секреты каналов или machine-specific runtime state.
- на этой машине OpenClaw требует Node 22.12+; overlay-скрипты по умолчанию подхватывают `/home/leon/.nvm/versions/node/v24.8.0/bin`, если он установлен.

Быстрые команды:

```bash
bash /git/tools/openclaw/ops/install.sh
bash /git/tools/openclaw/ops/verify.sh
```

Основной runbook:

- [reinstall-and-restore.md](/git/tools/openclaw/docs/reinstall-and-restore.md)
- [openclaw-concurrency-audit-2026-03-09.md](/git/tools/openclaw/docs/openclaw-concurrency-audit-2026-03-09.md)
- [decommission-openclaw-2026-03-15.md](/git/tools/openclaw/reports/decommission-openclaw-2026-03-15.md)
