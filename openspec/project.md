# Project Context

## Bootstrap Status
Этот файл пока фиксирует только минимальный OpenSpec bootstrap для репозитория. Это не полный handbook и не самостоятельный source-of-truth по архитектуре.

## Source of truth
- `../README.md`
- `../AGENTS.md`
- `/int/AGENTS.md`

## OpenSpec usage in this repo
- OpenSpec здесь не является default execution path.
- `SPEC-MUTATION` допустим только по явному одобрению владельца и только если задача затрагивает `public API/contracts`, `schema/DB`, границы capability или breaking changes.
- Без такого одобрения новые `change-id`, `proposal.md`, `tasks.md`, `design.md` и новые capability specs не создаются.
- Если уже существует релевантный `openspec/specs/**` или `openspec/changes/**`, используйте его только как вспомогательный контекст в рамках approved scope.

## Current catalog state
- `openspec/specs/README.md` и `openspec/changes/README.md` описывают bootstrap-catalog.
- За фактическим назначением репозитория, ownership и runtime-ограничениями всегда смотрите в root `README.md` и `AGENTS.md`.
