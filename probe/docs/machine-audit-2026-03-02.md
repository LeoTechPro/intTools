# Machine Audit 2026-03-02: Probe Monitor + openclaw

Scope: `Probe Monitor` + `openclaw gateway`.

Этот snapshot сохранён как historical reference после выноса audit-артефактов из `/git/probe` во внешний tooling-контур. Исторические пути ниже намеренно оставлены в старом виде `/git/scripts/...`; канонический путь после миграции — `/git/tools/...`.

| Asset | Current Location | Git Status | Risk | Mitigation |
|---|---|---|---|---|
| Orphan cleaner logic | `/git/scripts/codex/cleanup_agent_orphans.sh` | Tracked | Script can be lost on host failure | Keep canonical script in `scripts/codex` and install cron from repo |
| Orphan cleaner schedule | `crontab -l` (`probe-agent-orphan-cleaner`) | Outside git | Manual drift, duplicates, loss after rebuild | Manage via `/git/scripts/codex/install_orphan_cleaner_cron.sh` |
| OpenClaw gateway unit | `~/.config/systemd/user/openclaw-gateway.service` | Outside git (generated) | Unit drift and non-reproducible setup | Keep canonical config in `tools/openclaw/openclaw.json`; restart via systemd |
| OpenClaw runtime config | `~/.codex/tools/openclaw/openclaw.json` | Tracked by policy | Wrong ACL/runtimes can break bot routing | Keep config in critical assets and back up before edits |
| OpenClaw runtime state | `~/.codex/tools/openclaw/state` | Ignored (runtime) | Session memory loss on disk failure | Include in runtime backup checklist |
| Probe Monitor compose stack | `/git/probe/config/docker-compose.yml` | Tracked | Path hardcode blocks portability | Use env-driven runtime mounts and external state roots |
| Fleet runtime data | `~/.local/share/probe-monitor/**` | Ignored (runtime) | Runtime loss on disk failure | Keep runtime artifacts outside git and document backup/restore |
| Alert bridge state map | `~/.local/state/probe-monitor/topic_map.json` | Ignored (runtime) | Alert routing memory loss | Keep canonical state outside git and back it up separately |
| Secrets (`.env`) | `/git/probe/.env`, `tools/openclaw/openclaw.json` | Tracked by policy | Secret exposure if repo leaked | Allowed by owner decision for private repo |

## Out of Scope Backlog

- Orbit machine-level config/runtime: `/etc/default/orbit`, `/opt/orbit/**`
- Global codex binary baseline outside `.codex`

## Acceptance Snapshot (2026-03-02)

- Probe Monitor compose working dir: `/git/probe`
- Runtime mounts: external state/runtime roots via `.env`
- `openclaw-gateway.service` active
- Legacy `telegram-bridge*` units removed
