# Change: Forbid agent-side filtering of owner-directed publication

## Why

В machine-wide и repo-local governance сейчас остаётся опасная лазейка: агентам местами разрешено трактовать publication как "опубликовать только свои релевантные правки". На owner-команде `push/publish/выкатывай/публикуй` это недопустимо:

- агент не должен сам решать, какие чужие, неатрибутированные или ранее существовавшие правки скрыть или отложить;
- попытка "бережно" исключить не свои изменения фактически меняет состав публикации без owner approval;
- при blocker-case правильный путь только один: либо публиковать текущее состояние как есть, либо сразу эскалировать владельцу, а не принимать решение за него.

Нужен жёсткий process-contract, который запретит agent-side filtering на explicit owner-directed publication и синхронизирует эту норму в AGENTS/README/skills/checklists.

## What Changes

- `openspec/specs/process/spec.md` получает явное требование: owner-directed publication не фильтруется агентом по его усмотрению.
- Machine-wide и repo-local governance docs фиксируют один и тот же контракт: локальный commit остаётся по согласованному scope, но при explicit `push/publish/выкатывай/публикуй` агент либо публикует уже подготовленное publication-state, либо останавливается и спрашивает.
- `agent-issues` skill и session-close checklist перестают путать local commit discipline с publication-path.

## Scope Boundaries

- Scope этого change — только governance/process слой и agent instructions.
- Change не меняет transport/runtime implementation publish wrappers и не добавляет новые deploy capabilities.
- Change не отменяет право владельца отдельно указать, что часть состояния нужно исключить; он запрещает только самостоятельное решение агента вместо такого указания.

## Acceptance (high-level)

- Canonical process spec содержит requirement против agent-side filtering на owner-directed publication.
- `AGENTS.md`, `README.md` и runtime skill/checklist не содержат conflicting guidance, которая смешивает local commit scope и publication filtering.
- При explicit owner-команде на publication policy везде сводится к одному правилу: commit scope может быть своим/согласованным, но уже подготовленное publication-state публикуется as-is or ask.
