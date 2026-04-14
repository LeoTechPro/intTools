# Change: Require OpenSpec agreement for tracked tooling mutations in `/int/tools`

## Why

Текущий `/int/tools` использует `openspec/` только как bootstrap-layer и допускает mutate-first execution path для части repo-owned tooling. Для machine-wide tooling-контура это слишком слабо:

- wrappers, gates, launchers, prompts/rules/skills и publish flows меняют поведение агентов и host automation;
- governance docs (`AGENTS.md`, `README.md`) можно обновить без синхронного spec source-of-truth, что создаёт drift;
- repo не фиксирует единый обязательный процесс: сначала agreed spec/change, потом tracked mutation.

Нужен жёсткий governance gate: любые tracked tooling/process mutations в `/int/tools` идут только через owner-approved OpenSpec package.

## What Changes

- `openspec/specs/process/spec.md` становится каноническим process spec для `/int/tools`.
- `openspec/changes/require-openspec-for-tooling-mutations/*` переводит repo с bootstrap-mode на mandatory OpenSpec path для tracked tooling/process mutations.
- `openspec/AGENTS.md` и `openspec/project.md` больше не описывают OpenSpec как optional bootstrap для этого repo.
- `AGENTS.md` и `README.md` фиксируют, что tracked tooling mutations разрешены только после формирования и согласования OpenSpec package.

## Scope boundaries

- Scope этого change — только governance/process layer репозитория `/int/tools`.
- Change не меняет runtime behavior конкретных wrappers/launchers/publish flows, кроме процессного требования сперва согласовать spec/change.
- Изменения host-local `.git/**`, runtime state вне git и untracked temp-артефактов не считаются частью этого process capability.

## Acceptance (high-level)

- В repo существует canonical spec `openspec/specs/process/spec.md`.
- В repo существует active change package, который описывает mandatory OpenSpec path для tracked tooling mutations.
- `AGENTS.md`, `README.md`, `openspec/AGENTS.md` и `openspec/project.md` согласованы с этим source-of-truth.
- Новая tracked tooling mutation без active agreed change считается policy blocker.
