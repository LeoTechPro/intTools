# intdb

`intdb` — self-contained operator CLI для remote Postgres/Supabase профилей с этой Windows-машины без SSH на DB-host.

## Что умеет v1

- `doctor` — проверить native PostgreSQL CLI, TCP и SQL-доступ к профилю;
- `sql` — выполнить ad-hoc SQL;
- `file` — выполнить SQL-файл;
- `dump` / `restore` — выгрузить и залить dump;
- `clone` — перенести dump из одной БД в другую через локальную машину;
- `copy` — выгрузить query в CSV и залить в target table;
- `migrate status` — сравнить `migration_manifest.lock` из `/int/data` с remote `public.schema_migrations`;
- `migrate data` — применить incremental или bootstrap migration flow `/int/data`.

## Layout

- `intdb.ps1` / `intdb.cmd` — основные launchers;
- `lib/intdb.py` — Python core;
- `.env.example` — bootstrap-шаблон профилей;
- `.env` — локальный untracked runtime-файл;
- `.tmp/` и `logs/` — локальные runtime-артефакты, не идут в git.

## Требования

- Windows PowerShell;
- `python` или `py` в `PATH`;
- `psql`, `pg_dump`, `pg_restore` в `PATH` или в стандартном каталоге `C:\Program Files\PostgreSQL\<version>\bin`;
- сетевой доступ до нужных PostgreSQL endpoint'ов;
- для `migrate *`: либо sibling checkout `..\..\data`, либо явный `--repo`, либо `INTDB_DATA_REPO`;
- для `migrate data --mode incremental`: `bash` из Git for Windows или иной совместимый `bash`.

## Профили

Формат переменных:

```env
INTDB_PROFILE__INTDATA_DEV__PGHOST=api.intdata.pro
INTDB_PROFILE__INTDATA_DEV__PGPORT=5432
INTDB_PROFILE__INTDATA_DEV__PGDATABASE=intdatadb-dev
INTDB_PROFILE__INTDATA_DEV__PGUSER=intdata_dev
INTDB_PROFILE__INTDATA_DEV__PGPASSWORD=<secret>
INTDB_PROFILE__INTDATA_DEV__PGSSLMODE=require
INTDB_PROFILE__INTDATA_DEV__WRITE_CLASS=nonprod
```

CLI обращается к такому профилю как `intdata-dev`.

`WRITE_CLASS`:

- `nonprod` — достаточно `--approve-target <profile>`;
- `prod` — дополнительно требуется `--force-prod-write`.

## Guardrail entrypoints (Punkt-B)

Для безопасной модели доступа используйте Python wrappers из `D:\int\tools\intdb\bin`:

- `pg-prod-ro.py` -> `punktb-prod-ro` (`db_readonly_prod`)
- `pg-legacy-ro.py` -> `punktb-legacy-ro` (`db_readonly_legacy`)
- `pg-dev-ro.py` -> `intdata-dev-ro` (`db_readonly_dev`)
- `pg-prod-migrate.py` -> `punktb-prod-migrator` (`db_migrator_prod`)
- `pg-dev-migrate.py` -> `intdata-dev-migrator` (`db_migrator_dev`)
- `pg-prod-admin.py` -> `punktb-prod-admin` (`db_admin_prod`, breakglass)
- `pg-dev-admin.py` -> `intdata-dev-admin` (`db_admin_dev`, breakglass)
- `pg-test-bootstrap.py` -> `punktb-test-bootstrap` (disposable `punkt_b_test`)

Запуск одинаковый на Windows и Linux:

```bash
python /int/tools/intdb/bin/pg-prod-ro.py --doctor
python /int/tools/intdb/bin/pg-dev-migrate.py --path /path/to/change.sql --write --confirm-target intdata
```

### Важно

- Supabase system roles (`authenticator`, `anon`, `authenticated`, `service_role`, `supabase_*`) в этой модели считаются immutable.
- Wrappers должны использовать только custom роли.
- Raw `psql` с ad-hoc DSN для agent workflow запрещен process-policy.

## Safety

- Все mutating-команды требуют явный `--approve-target`.
- Для профилей класса `prod` обязателен `--force-prod-write`.
- `sql` и `file` по умолчанию запускаются в `default_transaction_read_only=on`.
- Типовые runtime-ошибки `psql/pg_dump/pg_restore`, `bash` и TCP-доступа переводятся в обычные `intdb:` сообщения без Python traceback.
- Секреты профиля передаются внешним PostgreSQL CLI через окружение процесса и не вшиваются в argv.
- Для `migrate data --mode incremental` `intdb` сам добавляет найденный PostgreSQL `bin` в `PATH` дочернего `bash`, если глобальный `PATH` на машине ещё не обновлён.
- Временные dump/CSV-файлы складываются в `.tmp/`.
- `.env` не должен попадать в git.
