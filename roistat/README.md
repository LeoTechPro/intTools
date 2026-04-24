# Roistat core

This directory keeps the reusable Roistat CRM/webhook integration core migrated
from `D:\int\roistat`.

Kept:
- `App/**`
- `autoload.php`
- `crm.php`
- `webhooks/bizon_webhook.php`
- safe runtime config loader and local smoke helper

Not kept:
- dashboard and Bitrix monitoring experiments
- old nginx/TLS/deploy contour from `ops/**`
- tracked logs, cache, SQLite, cursor, or secrets

## Runtime config

Tracked code reads runtime values from:

```text
D:\int\tools\.runtime\roistat\config.php
```

Override with:

```text
ROISTAT_RUNTIME_DIR=/path/to/runtime/root
ROISTAT_CONFIG_PATH=/path/to/config.php
```

Use `config.example.php` as the template. Real config and runtime state must stay
outside git.

Runtime state:

```text
.runtime/roistat/config.php
.runtime/roistat/data/viewers.db
.runtime/roistat/data/cursor.json
.runtime/roistat/logs/*.log
```

## Smoke

```bash
ROISTAT_BASE_URL=http://127.0.0.1:8080 ROISTAT_TOKEN=<token> ./bin/smoke.sh
```

`ROISTAT_TOKEN` is the md5 of `ROISTAT_CRM_USER . ROISTAT_CRM_PASS` for the
runtime config.
