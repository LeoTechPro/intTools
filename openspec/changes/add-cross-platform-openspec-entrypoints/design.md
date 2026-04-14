# Design: cross-platform repo-managed OpenSpec launchers

## Context

OpenSpec уже vendored/installed в `/int/tools/codex/tools/openspec`, а Linux launcher `codex/bin/openspec` tracked в git. Для Windows симметричных repo-managed wrappers нет, из-за чего запуск зависит от machine-local improvisation.

## Decision

Добавляются два tracked Windows entrypoint-а:

- `codex/bin/openspec.ps1`
- `codex/bin/openspec.cmd`

Они повторяют контракт Linux launcher:

1. вычисляют repo-local path;
2. запускают локально установленный OpenSpec CLI;
3. если CLI не установлен, возвращают явный install error.
