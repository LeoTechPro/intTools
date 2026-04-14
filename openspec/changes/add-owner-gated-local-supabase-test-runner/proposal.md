# Change: Add owner-gated local Supabase test runner to `intdb`

## Why

После отказа от remote disposable DB `/int/data` всё ещё нужен controlled path для clean bootstrap/smoke/regression с нуля. Этот путь должен:

- поднимать local temporary Supabase platform layer через Docker;
- накладывать поверх него repo-owned lifecycle `/int/data`;
- запускаться только по явной owner-команде и не использовать unattended defaults.

## What Changes

- В `/int/tools/openspec/specs/intdb/spec.md` появляется canonical capability для owner-gated local Supabase test runner.
- `intdb` получает новую команду local disposable bootstrap/smoke workflow.
- Команда использует `supabase init` + `supabase start`, затем применяет `/int/data/init/010_supabase_migrate.sh`, `init/seed.sql` и при необходимости SQL smoke.
- Документация `intdb` фиксирует prerequisites, confirmation gates, cleanup semantics и ограничения по unattended use.

## Scope boundaries

- Scope change — только operator tooling внутри `intdb`.
- Change не заменяет publish/deploy flow и не даёт automation-path для auto smoke against live DB.

## Acceptance (high-level)

- `intdb` имеет owner-gated local runner для disposable Supabase bootstrap.
- Runner отказывается стартовать без явного подтверждения owner control.
- Runner не зависит от retired remote test contour.
