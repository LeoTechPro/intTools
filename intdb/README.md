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

## Быстрый старт

1. Скопируйте `.env.example` в `.env`.
2. Заполните реальные `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`.
3. Проверьте профиль:

```powershell
pwsh -File D:\int\tools\intdb\intdb.ps1 doctor --profile intdata-dev
```

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

## Примеры

Проверить dev-профиль:

```powershell
pwsh -File D:\int\tools\intdb\intdb.ps1 doctor --profile intdata-dev
```

Прочитать данные:

```powershell
pwsh -File D:\int\tools\intdb\intdb.ps1 sql `
  --profile intdata-dev `
  --sql "select now(), current_database();"
```

Выполнить mutating SQL:

```powershell
pwsh -File D:\int\tools\intdb\intdb.ps1 sql `
  --profile intdata-dev `
  --write `
  --approve-target intdata-dev `
  --sql "update public.some_table set touched_at = now() where id = 1;"
```

Проверить pending migration'ы `/int/data`:

```powershell
pwsh -File D:\int\tools\intdb\intdb.ps1 migrate status `
  --target intdata-dev `
  --repo D:\int\data
```

Применить incremental migration flow `/int/data`:

```powershell
pwsh -File D:\int\tools\intdb\intdb.ps1 migrate data `
  --target intdata-dev `
  --mode incremental `
  --repo D:\int\data `
  --approve-target intdata-dev
```

Если `--repo` не указан, `intdb` сначала смотрит `INTDB_DATA_REPO` из process env или локального `.env`, затем пытается найти sibling repo `..\..\data` относительно самого инструмента. Если ни один вариант не найден, команда завершится с явной ошибкой и попросит указать `--repo`.

## Safety

- Все mutating-команды требуют явный `--approve-target`.
- Для профилей класса `prod` обязателен `--force-prod-write`.
- `sql` и `file` по умолчанию запускаются в `default_transaction_read_only=on`.
- Типовые runtime-ошибки `psql/pg_dump/pg_restore`, `bash` и TCP-доступа переводятся в обычные `intdb:` сообщения без Python traceback.
- Секреты профиля передаются внешним PostgreSQL CLI через окружение процесса и не вшиваются в argv.
- Временные dump/CSV-файлы складываются в `.tmp/`.
- `.env` не должен попадать в git.
