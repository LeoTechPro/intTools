# Implementation Order (DRAFT ONLY)

## 1. Freeze + Preflight
1. Freeze release/migration/cron активности в окне rename.
2. Снять snapshot активности (`pg_stat_activity`) и map зависимых сервисов.
3. Подтвердить наличие БД `punctb_prod` и `punkt_b` на одном кластере `192.168.0.8`.
4. Подготовить rollback owners и временное окно.

## 2. Rename Database Window
1. Остановить writers нового стека (`/int/punkt-b`) и legacy backend (`/int/punkt_b_legacy`).
2. Завершить активные подключения к `punctb_prod` и `punkt_b`.
3. Выполнить rename SQL.
4. Обновить DSN/env/wrappers:
   - `punctb_prod` -> `punkt_b_prod`
   - `punkt_b` -> `punkt_b_legacy_prod`
5. Запустить сервисы:
   - legacy backend,
   - затем новый стек.
6. Smoke:
   - legacy runtime write работает,
   - agent readonly к legacy работает,
   - новый prod runtime работает.

## 3. Legacy Hard Lock
1. Переименовать роль `punkt_b` -> `legacy_backend_role`.
2. Обновить legacy backend DSN на `legacy_backend_role`.
3. Создать `db_readonly_legacy`.
4. Оставить write в legacy только `legacy_backend_role`.
5. Для `db_readonly_legacy` выдать только `CONNECT/USAGE/SELECT`.
6. Включить role-level `default_transaction_read_only=on` для readonly ролей.

## 4. Target Role Split (Prod/Dev)
- PROD (`punkt_b_prod`):
  - `db_admin_prod` (admin/bootstrap only)
  - `db_migrator_prod` (controlled migrations)
  - `db_readonly_prod` (agent/audit)
- DEV (`intdata`):
  - `db_admin_dev`
  - `db_migrator_dev`
  - `db_readonly_dev`

## 5. Migration Flow
- `punkt_b_prod`: миграции только через controlled script + `db_migrator_prod`.
- `intdata`: тот же контракт preflight/gate, упрощенный операционно.
- `punkt_b_legacy_prod`: миграции запрещены; только runtime legacy + readonly audit.

## 6. Data Migration Legacy -> New Prod
Primary path: app-level idempotent ETL.
- Source role: `db_readonly_legacy`.
- Target role: `db_migrator_prod`.
- Механика: staging + upsert + watermark + повторяемые батчи.
Fallback options (FDW/dblink/dump): только по отдельному одобрению и с повышенным риском.

## 7. Guardrails
1. Shell entrypoints:
   - `pg-prod-ro`
   - `pg-legacy-ro`
   - `pg-prod-migrate`
2. Read-only by default для агентов.
3. Write-операции только через explicit flags (`--write`, `--prod`).
4. Обязательный preflight banner (`HOST/DB/ROLE/MODE`).

## 8. Rollback Strategy
- Rename rollback: обратный rename парой команд после остановки writers.
- Role rollback: временный compatibility alias при необходимости.
- Privilege rollback: хранить explicit reverse REVOKE/GRANT blocks в change-set.

## 9. Residual UNKNOWN (must resolve before apply)
- Полный inventory SECURITY DEFINER + `search_path`.
- Полная grant-matrix non-public schemas в target DB.
- Точный список runtime зависимостей, где hardcoded старые DB/role names.
