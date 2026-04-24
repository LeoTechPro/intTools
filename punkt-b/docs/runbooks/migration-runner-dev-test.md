# migration-runner-dev-test

## DEV (`intdata`)

```bash
python /int/tools/dba/bin/pg-dev-migrate.py --path <sql-file> --write --confirm-target intdata
```

- использовать `db_migrator_dev`.
- `intdata` не дропать и не пересоздавать.

## TEST (local disposable Supabase runtime)

```bash
pwsh -File /int/tools/dba/dba.ps1 local-test run --confirm-owner-control I_ACKNOWLEDGE_LOCAL_ONLY --smoke-file tests/sql/<file>.sql
```

- remote `punkt_b_test`/`intdata_test` retired и больше не используются.
- bootstrap/reset допустимы только в локальном owner-gated runtime на owner PC.
