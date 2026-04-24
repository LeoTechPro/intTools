# AGENTS — intDBA

## Scope

- `dba/**` — self-contained operator CLI для remote Postgres/Supabase профилей;
- launcher'ы живут рядом с инструментом, thin wrappers допускаются вне каталога только как прокси-входы.

## Rules

- В git допускается только `.env.example`; локальный `.env` должен оставаться untracked.
- Runtime-артефакты инструмента живут только в ignored путях `.tmp/`, `logs/`, `__pycache__/`.
- Для `/int/data` migration flow не дублируется: dev backend work должен идти в remote checkout `agents@vds.intdata.pro:/int/data`.
- Локальный Windows checkout `D:\int\data` не является рабочим default; не добавляйте на него новые AGENTS/scripts references. Если нужен disposable local flow, передавайте явный `--repo`/`DBA_DATA_REPO`.

## Checks

- Минимум для handoff: unit tests `python -m unittest discover -s D:\int\tools\dba\tests`.
- Для CLI smoke используйте `--help` и read-only команды, если локальный `.env` не заполнен.
