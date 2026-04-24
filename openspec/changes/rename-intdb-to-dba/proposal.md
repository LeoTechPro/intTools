# Change: Rename intdb contour to dba and align intDBA branding (INT-344)

## Why

Текущий contour одновременно использует несколько разных имён для одной и той же DBA-capability:

- filesystem/profile/router name: `intdb`
- short human-facing name: `intdb`
- full plugin family branding: `intData DBA`

Это создаёт лишнюю путаницу в repo structure, routing policy, plugin catalog и runbooks. Владелец запросил унифицировать contour на `dba`, при этом human-facing short name должен стать `intDBA`, а полное имя — `intData Tools DBA`.

## What Changes

- Rename tracked contour path `/int/tools/intdb` to `/int/tools/dba`.
- Rename canonical engine/adapters/profile identifiers from `intdb` to `dba`, где это часть repo-owned contract внутри `/int/tools`.
- Update docs, tests, runbooks, routing config, plugin metadata and OpenSpec source-of-truth to stop advertising `intdb`.
- Normalize human-facing naming:
  - short name: `intDBA`
  - full name: `intData Tools DBA`

## Scope

- `/int/tools/dba/**` and former `/int/tools/intdb/**`
- `codex/bin/**`, `codex/config/**`, `codex/plugins/**`, templates and verification scripts
- `README.md`, `RELEASE.md`, repo-local docs/runbooks that reference the contour
- `openspec/specs/**` and relevant `openspec/changes/**` references that currently encode `intdb`

## Out of Scope

- SQL behavior changes, profile credential changes, or DB permission changes
- Untracked local runtime state under `/int/tools/.runtime/**`
- Product-repo changes outside this repo

## Acceptance

- No active tracked repo references advertise the contour as `intdb`; tracked path/adapter/profile references use `dba`.
- Human-facing docs/plugin labels describe the utility as `intDBA`.
- Full plugin/catalog branding uses `intData Tools DBA`.
- Existing DBA operator workflows still resolve through the renamed contour and pass focused tests/help checks.
