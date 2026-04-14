# Change: Add cross-platform repo-managed OpenSpec entrypoints

## Why

`/int/tools` уже хранит tracked Linux launcher `codex/bin/openspec`, но для Windows нет симметричных repo-managed entrypoints. Из-за этого запуск OpenSpec на Windows зависит от ad-hoc machine-local path assumptions, а не от versioned tooling.

Нужно закрепить, что OpenSpec launcher:

- попадает в git;
- запускается из repo-managed path на Linux и Windows;
- не требует неversioned local wrapper для базового вызова.

## What Changes

- Добавляются tracked Windows entrypoints `codex/bin/openspec.ps1` и `codex/bin/openspec.cmd`.
- `openspec/specs/process/spec.md` фиксирует требование про cross-platform tracked entrypoints.
- `README.md` документирует Linux/Windows команды запуска.

## Scope boundaries

- Scope этого change — только repo-managed OpenSpec launchers и их process contract.
- Change не меняет OpenSpec CLI package и не меняет содержимое `tools/openspec/node_modules`.

## Acceptance (high-level)

- В git есть repo-managed OpenSpec entrypoints для Linux и Windows.
- Windows entrypoints вызывают тот же локально установленный OpenSpec CLI или дают явную install-error.
- Canonical process spec и README согласованы с этим поведением.
