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
- `local-test run` — поднять temporary local Supabase runtime под owner-контролем, применить `/int/data` migrations + `init/seed.sql` и опционально прогнать SQL smoke.
- `local-test stop` — остановить temporary local Supabase runtime без backup.

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
- `pg-test-bootstrap.py` -> retired stop-signal; remote disposable test contour больше не поддерживается

Запуск одинаковый на Windows и Linux:

```bash
python /int/tools/intdb/bin/pg-prod-ro.py --doctor
python /int/tools/intdb/bin/pg-dev-migrate.py --path /path/to/change.sql --write --confirm-target intdata
```

### Важно

- Supabase system roles (`authenticator`, `anon`, `authenticated`, `service_role`, `supabase_*`) в этой модели считаются immutable.
- Wrappers должны использовать только custom роли.
- Raw `psql` с ad-hoc DSN для agent workflow запрещен process-policy.
- `vds.intdata.pro` больше не используется как disposable test contour для `/int/data`; live remote contour остаётся только `intdata`.

## Local disposable Supabase runner

Canonical disposable workflow для `/int/data` smoke/bootstrap с нуля:

```bash
pwsh -File D:\int\tools\intdb\intdb.ps1 local-test run --confirm-owner-control I_ACKNOWLEDGE_LOCAL_ONLY
```

Основные свойства:

- нужен Docker;
- нужен Supabase CLI (`supabase`) или fallback через `npx supabase`;
- workspace создаётся в ignored `intdb/.tmp/local-supabase/<stamp>`;
- после `supabase start` tool применяет `/int/data/init/010_supabase_migrate.sh apply`, затем `init/seed.sql`;
- SQL smoke можно передать через `--smoke-file`;
- по умолчанию runtime останавливается сам; для ручной диагностики используйте `--keep-running` и затем `local-test stop`.

## Safety

- Все mutating-команды требуют явный `--approve-target`.
- Для профилей класса `prod` обязателен `--force-prod-write`.
- `sql` и `file` по умолчанию запускаются в `default_transaction_read_only=on`.
- `local-test run` требует `--confirm-owner-control I_ACKNOWLEDGE_LOCAL_ONLY` и не имеет unattended default path.
- Типовые runtime-ошибки `psql/pg_dump/pg_restore`, `bash` и TCP-доступа переводятся в обычные `intdb:` сообщения без Python traceback.
- Типовые runtime-ошибки `docker` и `supabase` для local runner тоже переводятся в обычные `intdb:` сообщения.
- Секреты профиля передаются внешним PostgreSQL CLI через окружение процесса и не вшиваются в argv.
- Для `migrate data --mode incremental` `intdb` сам добавляет найденный PostgreSQL `bin` в `PATH` дочернего `bash`, если глобальный `PATH` на машине ещё не обновлён.
- Временные dump/CSV-файлы складываются в `.tmp/`.
- `.env` не должен попадать в git.
