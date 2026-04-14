# Design: owner-gated local Supabase runner in `intdb`

## Workflow

1. Operator запускает `intdb local-test run ...` с явным подтверждением owner control.
2. Tool создаёт temporary workspace в `intdb/.tmp/local-supabase/<stamp>`.
3. Tool вызывает `supabase init` в workspace и `supabase start` для поднятия локального platform layer.
4. Tool извлекает локальный DB connection info из `supabase status`.
5. Tool применяет `/int/data/init/010_supabase_migrate.sh apply`, затем `init/seed.sql`.
6. Tool опционально выполняет SQL smoke files.
7. Tool либо оставляет runtime поднятым (`--keep-running`), либо вызывает controlled `supabase stop --no-backup`.

## Guardrails

- Нужны Docker и Supabase CLI; если `supabase` не установлен, допускается fallback `npx supabase`.
- Команда требует явного токена подтверждения owner control и не имеет implicit auto-run path.
- Workspace и runtime state живут только в ignored `.tmp/`.
