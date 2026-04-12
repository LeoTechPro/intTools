# PostgreSQL Safe Architecture (Supabase Roles Immutable) — DRAFT ONLY

Статус: draft-only. Ничего из этого пакета не применяется автоматически.

## Базовый инвариант

Supabase system roles считаются immutable. Запрещено менять им:

- flags (`CREATEROLE`, `CREATEDB`, ...)
- memberships
- grants/revokes
- ownership

Далее hardening строится только вокруг custom roles и process guardrails.

## Контуры

- prod new: `punkt_b_prod` (owner `punktb_pro`)
- prod legacy: `punkt_b_legacy_prod` (owner `legacy_backend_role`)
- dev: `intdata` (owner `supabase_admin`)
- test: `punkt_b_test` (owner `intdata_test_bootstrap`)

## Состав пакета

- `00_inventory_checks.sql`
- `10_role_flag_hardening_prod.sql`
- `20_role_flag_hardening_legacy.sql`
- `30_role_flag_hardening_dev.sql`
- `40_readonly_enforcement_legacy.sql`
- `50_migrator_model.sql`
- `60_agent_guardrails.sql`
- `70_validation_queries.sql`
- `80_dr_prerequisites.sql`
- `IMPLEMENTATION_ORDER.md`

## Примечания

- Все SQL ниже допускают только custom-role mutations.
- Если шаг требует изменения Supabase system role, это считается limitation и выполняется через workaround на wrapper/process уровне.
