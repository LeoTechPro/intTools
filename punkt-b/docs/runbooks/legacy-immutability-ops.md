# legacy-immutability-ops

## Цель

`punkt_b_legacy_prod` — immutable источник для агентов.

## Правила

- agent: только `db_readonly_prod` через legacy readonly wrapper.
- legacy backend: `legacy_backend_role` для runtime write.
- Supabase system roles не мутируем.

## Операционный контроль

- wrappers mandatory (`pg-legacy-ro` для read).
- миграционные команды должны hard-fail на legacy target.
- любой write в legacy только через выделенный maintenance window.
