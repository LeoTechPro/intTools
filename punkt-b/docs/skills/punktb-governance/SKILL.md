---
name: punktb-governance
description: "Процессные инварианты PunktB: запрет новых OpenSpec changes/specs без явного одобрения владельца, приоритет *-core, консолидация non-core."
---

# PunktB Governance

## Goal
Сделать правила работы воспроизводимыми для людей и агентов:
- новые OpenSpec `change-id` и новые capability-спеки не создаются без явного одобрения владельца;
- по умолчанию расширяются существующие `*-core` changes и существующие `openspec/specs/*`;
- любые “разовые” non-core changes в `openspec/changes/*` должны быть консолидированы в подходящие `*-core` и помечены как DEPRECATED (без удаления).

## Refactor Canon
- Единственная актуальная refactor-system для PunktB: [README.md](../../README.md) -> `Agent Architecture Target` / `WS0–WS5`, [web/README.md](../../web/README.md) -> `Agent Architecture Target`, nested hot-zone `AGENTS.md` и текущая WS0–WS5 issue-очередь.
- Отдельные refactor artifacts вне `WS0–WS5` не должны сохраняться в актуальном контуре. Термины `refactor-flatten-shared`, `refactor-web-areas-structure`, `refactor-client-areas`, `Wave 0/A-F/G`, `P0-P4` трактуются только как мусор/drift под удаление или перепривязку.
- Если поиск по `refactor/рефактор` выводит на такие артефакты, агент должен перепривязать задачу к текущему canonical source-of-truth, а не воспроизводить старую taxonomy.

## Rules (Non-Negotiable)
1. **NO new OpenSpec scaffolding без одобрения владельца.**
   - Запрещено создавать новые каталоги `openspec/changes/<new-change-id>/` и новые capability-каталоги в `openspec/specs/<new-capability>/` без явного “да” от владельца.
   - Если задача требует нового change-id или новой capability: остановись и спроси владельца.

2. **Default path: extend core.**
   - Если нужно “добавить ещё одно правило/кейс” по уже существующей зоне, расширяй соответствующий `*-core` change и/или существующую спеки в `openspec/specs/*`.

3. **Non-core в changes = временно и должно быть поглощено core.**
   - Для `openspec/changes/<non-core>/` целевое состояние:
     - контент перенесён/сослан в core;
     - в non-core добавлена пометка `Status: DEPRECATED` + ссылка на core;
     - ничего не удаляется (история остаётся).

## Mapping (current)
- `openspec/changes/add-auto-manager-role-by-domain` -> `rbac-core` (источник: `openspec/specs/rbac-core/spec.md`)
- `openspec/changes/update-conclusions-perms` -> `rbac-core` (источник: `openspec/specs/rbac-core/spec.md`)
- `openspec/changes/refactor-diagnostics-slug-route` -> `diagnostics-core` (источник: `openspec/changes/diagnostics-core/specs/app-shell/spec.md`)

## Migration Gate (Generic)
- Любые миграции выполняются только после DBA‑ревью всех невыполненных миграций и проверки отсутствия конфликтов.
- Единственный гейт на выполнение миграций по умолчанию — явное подтверждение DBA в трекере задач (например, Beads).
- Каждая миграция обязана фиксировать версию в таблице миграций проекта (`schema_migrations` или эквивалент).
- Архив миграций не исполняется; разовые/устаревшие миграции переносятся в архив.
- В активном каталоге миграций остаются только bootstrap/идемпотентные файлы.

## References
- Project rules: `AGENTS.md`, `GEMINI.md`
- OpenSpec workflow: `openspec/AGENTS.md`
