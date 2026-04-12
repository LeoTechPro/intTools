# dr-instance-operations

## Target topology

- отдельный Postgres instance на dev-host (отдельный port/data-dir)
- те же имена БД в DR instance:
  - `punkt_b_prod`
  - `punkt_b_legacy_prod`
- `intdata` и `punkt_b_test` остаются в основном dev instance

## Принципы

- не смешивать dev и DR в одном instance.
- не мутировать Supabase system roles вручную.
- репликация/восстановление на уровне instance/data, не через role mutation.
