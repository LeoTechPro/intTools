# dr-instance-operations

## Target topology

- отдельный Postgres instance на dev-host (отдельный port/data-dir)
- те же имена БД в DR instance:
  - `punkt_b_prod`
  - `punkt_b_legacy_prod`
- `intdata` остаётся в основном dev instance
- disposable test contour для `/int/data` вынесен в локальный owner-gated Supabase runtime и не держится на `vds.intdata.pro`

## Принципы

- не смешивать dev и DR в одном instance.
- не мутировать Supabase system roles вручную.
- репликация/восстановление на уровне instance/data, не через role mutation.
