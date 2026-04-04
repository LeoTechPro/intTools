---
name: review-sql-fix
description: 'Детерминированный pipeline исправления SQL-замечаний после review-sql-find. Используйте, когда нужно принять findings/sections, переподтвердить тезисы по текущему состоянию, безопасно применить runtime и repo SQL-исправления (только для dev/stage), собрать доказательства и выпустить артефакты remediation: verdict, applied runtime SQL, applied repo changes, postcheck report и rollback guide.'
---

# Review SQL Fix

Пишите все ответы на русском языке.

## Goal

Исправлять SQL-замечания из `review-sql-find` по доказательной схеме `backup -> precheck -> apply -> postcheck -> artifacts`.

## Input Contract

Передавайте JSON с обязательными полями:

- `environment`: `dev | stage | prod`
- `scope`: `int/data | int/assess | custom`
- `fix_mode`: `apply | plan_only` (default `apply`)
- `source`: `live_sql | section_summaries`
- `findings_bundle`: секции или пути к отчётам из `review-sql-find`

Опционально:

- `repo_targets`: список корней для file-level remediation
- `runtime_actions`: явный список SQL-действий
- `repo_fixes`: явный список file-fix действий
- `allow_dangerous`: `false` по умолчанию, включает override для опасных SQL
- `runtime_executor`: настройки выполнения live SQL (поддерживается `type=psql`)
- `role_snapshot` / `settings_snapshot` / `ddl_snapshot`: данные для runtime backup metadata
- `pg_dump_path`: путь к pg_dump/DDL архиву для копирования в snapshot (если файл существует)

## Output Contract

Всегда генерируйте 5 артефактов в `output_dir`:

1. `fix-verdict.md`
2. `applied-runtime-sql.md`
3. `applied-repo-changes.md`
4. `postcheck-report.md`
5. `rollback-guide.md`

## Workflow

1. Примените policy guard.
- `environment=prod` + `fix_mode=apply` => принудительно `effective_mode=plan_only`.
- Любые SQL-модификации в `prod` запрещены.

2. Выполните backup phase.
- Создайте снапшот в `/int/.tmp/<UTC>/review-sql-fix/`.
- Сохраните runtime metadata и копии целевых repo-файлов перед изменениями.

3. Выполните precheck.
- Нормализуйте findings из `findings_bundle`.
- Подтвердите каждый тезис и присвойте один из статусов:
  - `confirmed`
  - `partially confirmed`
  - `not confirmed`
  - `outdated`
  - `architecture opinion`

4. Выполните apply (если разрешено policy).
- Runtime DB lane: только `confirmed`/`partially confirmed`, малыми группами.
- При наличии `runtime_executor` выполняйте SQL live; иначе фиксируйте `applied_simulated` с причиной.
- Repo SQL lane: только `repo_targets`, обязательный `lockctl`, никаких несвязанных правок.
- Запрещайте опасные SQL без явного `allow_dangerous=true`.

5. Выполните postcheck.
- Зафиксируйте результаты проверок по runtime/repo lane.
- При ошибке остановите pipeline и сформируйте partial artifacts + rollback guide.

6. Сформируйте артефакты.
- Запишите все 5 markdown-отчётов, даже при частичном провале (с явным статусом).

## Script Usage

Запуск pipeline:

```bash
python scripts/fix_pipeline.py --input /path/to/fix-input.json --output-dir /path/to/out
```

## References

- `references/fix-playbook.md` — safety rules, SQL-risk policy, статусы и критерии подтверждения.
