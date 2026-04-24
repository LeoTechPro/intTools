# migration-runner-prod

## Цель

Контролируемый запуск миграций в `punkt_b_prod` только через custom роль `db_migrator_prod`.

## Инварианты

- Supabase system roles immutable.
- Raw `psql` и runtime роли для миграций запрещены.
- Нужны явные флаги write/prod.

## Команда

```bash
python /int/tools/dba/bin/pg-prod-migrate.py --path <sql-file> --write --prod --confirm-target punkt_b_prod
```

## Preflight

- banner показывает `ENV=PROD`, `ROLE=db_migrator_prod`, `DB=punkt_b_prod`.
- verify SQL file path и change window.

## Rollback

- только заранее подготовленным rollback SQL.
- после rollback сразу выполнить `70_validation_queries.sql`.
