# AGENTS — intdb

## Scope

- `intdb/**` — self-contained operator CLI для remote Postgres/Supabase профилей;
- launcher'ы живут рядом с инструментом, thin wrappers допускаются вне каталога только как прокси-входы.

## Rules

- В git допускается только `.env.example`; локальный `.env` должен оставаться untracked.
- Runtime-артефакты инструмента живут только в ignored путях `.tmp/`, `logs/`, `__pycache__/`.
- Для `/int/data` migration flow не дублируется: `intdb` переиспользует owner scripts из `D:\int\data`.

## Checks

- Минимум для handoff: unit tests `python -m unittest discover -s D:\int\tools\intdb\tests`.
- Для CLI smoke используйте `--help` и read-only команды, если локальный `.env` не заполнен.
