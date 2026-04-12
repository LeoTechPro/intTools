# PostgreSQL Final Safe Architecture (DRAFT ONLY)

Статус: draft-only. Этот пакет не применяется автоматически и не должен выполняться без отдельного окна внедрения и owner approval.

## Контуры
- legacy prod (immutable): `punkt_b_legacy_prod`
- new prod (target): `punkt_b_prod`
- dev: `intdata`
- test: `intdata_test`

## Базовые решения
- Rename на кластере `192.168.0.8`:
  - `punctb_prod -> punkt_b_prod`
  - `punkt_b -> punkt_b_legacy_prod`
- Legacy write only через `legacy_backend_role`.
- Агентский доступ по умолчанию: `db_readonly_prod`, `db_readonly_legacy`.
- Миграции в новом prod: только через `db_migrator_prod` и guarded entrypoint.

## Порядок внедрения (high-level)
1. Freeze (релизы/cron/ad-hoc SQL).
2. Inventory/preflight (connections, blockers, role matrix).
3. Rename DB (maintenance window, minimal downtime).
4. Обновление DSN/env/wrappers.
5. Legacy hard-lock (write-only для `legacy_backend_role`).
6. Включение role split (prod/dev) и migration guardrails.
7. Validation + smoke + rollback checkpoint.

## Файлы пакета
- `rename_databases.sql`
- `roles_prod.sql`
- `roles_dev.sql`
- `roles_legacy.sql`
- `grants_app_public.sql`
- `readonly_enforcement.sql`
- `migration_roles.sql`
- `validation.sql`

## Важно
- Все SQL в каталоге являются проектным черновиком (DRAFT ONLY).
- Перед apply обязателен отдельный inventory run и сверка UNKNOWN/TODO.
- Для legacy DB миграции запрещены; только runtime legacy backend + read-only аудит.
