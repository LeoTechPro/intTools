# agent-db-access-policy

## Default access (agent)

- `pg-prod-ro` -> `db_readonly_prod`
- `pg-legacy-ro` -> `db_readonly_legacy`
- `pg-dev-ro` -> `db_readonly_dev`

## Optional access

- `pg-prod-migrate` (explicit write/prod flags)
- `pg-dev-migrate` (explicit write flag)

## Canonical paths

- `/int/tools/intdb/bin/pg-prod-ro.py`
- `/int/tools/intdb/bin/pg-legacy-ro.py`
- `/int/tools/intdb/bin/pg-dev-ro.py`
- `/int/tools/intdb/bin/pg-prod-migrate.py`
- `/int/tools/intdb/bin/pg-dev-migrate.py`
- `/int/tools/intdb/bin/pg-prod-admin.py`
- `/int/tools/intdb/bin/pg-dev-admin.py`
- `intdb local-test run --confirm-owner-control I_ACKNOWLEDGE_LOCAL_ONLY` (owner-gated local disposable runner for `/int/data`)

## Forbidden

- raw psql/DSN
- any Supabase system role
- any superuser role
- write to `punkt_b_legacy_prod` outside legacy backend runtime
