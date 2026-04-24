# agent-db-access-policy

## Default access (agent)

- `pg-prod-ro` -> `db_readonly_prod`
- `pg-legacy-ro` -> `db_readonly_prod` on `punkt_b_legacy_prod`
- `pg-dev-ro` -> `db_readonly_dev`

## Optional access

- `pg-prod-migrate` (explicit write/prod flags)
- `pg-dev-migrate` (explicit write flag)

## Canonical paths

- `/int/tools/dba/bin/pg-prod-ro.py`
- `/int/tools/dba/bin/pg-legacy-ro.py`
- `/int/tools/dba/bin/pg-dev-ro.py`
- `/int/tools/dba/bin/pg-prod-migrate.py`
- `/int/tools/dba/bin/pg-dev-migrate.py`
- `/int/tools/dba/bin/pg-prod-admin.py`
- `/int/tools/dba/bin/pg-dev-admin.py`
- `dba local-test run --confirm-owner-control I_ACKNOWLEDGE_LOCAL_ONLY` (owner-gated local disposable runner for `/int/data`)

## Forbidden

- raw psql/DSN
- any Supabase system role
- direct superuser login outside canonical admin wrappers (`pg-prod-admin`, `pg-dev-admin`)
- write to `punkt_b_legacy_prod` outside legacy backend runtime
