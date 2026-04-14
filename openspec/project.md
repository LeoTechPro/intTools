# Project Context

## Governance Status
OpenSpec в `/int/tools` используется как обязательный governance-layer для tracked tooling/process mutations. Это не полный handbook по архитектуре хоста, но это canonical source-of-truth по lifecycle и process rules для repo-owned tooling changes.

## Source of truth
- `../README.md`
- `../AGENTS.md`
- `/int/AGENTS.md`

## OpenSpec usage in this repo
- Для любых tracked tooling/process mutations исполнение допускается только через owner-approved change package в `openspec/changes/<change-id>/`.
- `SPEC-MUTATION` обязателен не только для `public API/contracts`, `schema/DB`, capability boundaries и breaking changes, но и для wrapper/hooks/gates/launchers/skills/prompts/rules/publish flows и governance docs этого репозитория.
- Без owner approval новые `change-id`, `proposal.md`, `tasks.md`, `design.md` и новые capability specs не создаются.
- В `EXECUTE` используется уже согласованный active change; параллельный mutate-first path без change package запрещён.

## Current catalog state
- `openspec/specs/process/spec.md` фиксирует канонический процесс для tooling-governance.
- `openspec/changes/require-openspec-for-tooling-mutations/*` — стартовый change, который переводит `/int/tools` с bootstrap-mode на mandatory OpenSpec path для tracked tooling mutations.
- За фактическим назначением репозитория, ownership и runtime-ограничениями всегда смотрите в root `README.md` и `AGENTS.md`.
