## 1. SPEC
- [x] 1.1 Зафиксировать owner-approved change package для нового local Supabase runner.
- [x] 1.2 Добавить canonical `intdb` capability spec.

## 2. IMPLEMENTATION
- [x] 2.1 Добавить в `intdb` local owner-gated Supabase bootstrap command.
- [x] 2.2 Поддержать `supabase init` + `supabase start` + repo migrations + `init/seed.sql`.
- [x] 2.3 Добавить optional SQL smoke execution и controlled cleanup.
- [x] 2.4 Убрать зависимость от retired remote test bootstrap path.

## 3. DOCS AND TESTS
- [x] 3.1 Обновить `intdb/README.md` и `.env.example`.
- [x] 3.2 Добавить/обновить unit tests для parser, gating и local runner helpers.

## 4. VALIDATION
- [x] 4.1 Прогнать `python -m unittest discover -s D:\\int\\tools\\intdb\\tests`.
- [x] 4.2 Проверить `intdb --help`/subcommand help и отсутствие старого remote disposable workflow.
