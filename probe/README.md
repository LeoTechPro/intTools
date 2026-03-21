# Probe Scripts

`probe/` хранит versioned maintenance и audit-утилиты для `Probe Monitor`, которые не входят в prod-core репозиторий `/int/probe`.

## Контракт

- `/int/probe` содержит только код, deploy-конфиг и проверки.
- Versioned maintenance scripts и исторические audit snapshots для `Probe Monitor` живут здесь.
- Mutable state и runtime-data самого `Probe Monitor` живут вне git: `~/.local/state/probe-monitor` и `~/.local/share/probe-monitor`.
- Migration/cutover идёт через `/int/probe/ops/migrate_runtime.sh`, затем `ops/cutover.sh --install-units --restart-services` и `ops/verify.sh --runtime`.

## Состав

- `collect_audit.sh` — сбор audit snapshot по текущему checkout `/int/probe`
- `docs/critical_assets.txt` — список must-survive assets и внешних runtime-path
- `docs/machine-audit-2026-03-02.md` — исторический audit snapshot, перенесённый из `probe`
