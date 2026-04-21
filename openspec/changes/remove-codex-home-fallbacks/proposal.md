# Change: Remove Codex-home fallback reads

Owning Multica issue: `INT-260`

## Why

`CODEX_HOME` is Codex-owned state. After the previous cleanup, intTools no longer writes Codex-home overlays, but active tooling still automatically reads legacy state and secrets from `$CODEX_HOME/memories/**`, `~/.codex/memories/**`, or `$CODEX_HOME/var/**`.

That keeps hidden coupling to native Codex runtime state. Runtime state and secrets for intTools must stay under `/int/tools/.runtime/**` unless the owner explicitly points a tool at another source.

## What Changes

- Remove automatic legacy migration reads from Codex memories in `lockctl` and `gatesctl`.
- Keep canonical runtime state under `/int/tools/.runtime/{lockctl,gatesctl}` and keep explicit state-dir env overrides.
- Remove secret/env fallback reads from `$CODEX_HOME/var` and `~/.codex/var`.
- Require explicit `codex_home` or explicit session file input for IntBrain session-memory reads/imports.
- Update active docs, skills, tests, and verifier guardrails so implicit Codex-home fallbacks do not return.

## Out of Scope

- Mutating, deleting, or migrating live `C:\Users\intData\.codex` or any other Codex home.
- Removing Codex native runtime/session storage itself.
- Removing `lockctl`, `gatesctl`, IntBrain memory tools, or native Codex plugin/skill mechanisms.

## Acceptance

- `lockctl` and `gatesctl` do not enumerate `$CODEX_HOME/memories/**`, `~/.codex/memories/**`, or legacy Windows `.codex` memory paths.
- Active secret loaders do not fall back to `$CODEX_HOME/var` or `~/.codex/var`.
- IntBrain session memory tools reject implicit session reads unless `codex_home` or a concrete session `file` is supplied.
- Tests cover the removed fallbacks and the explicit-source requirement.
- Active verifiers fail on reintroduced implicit Codex-home fallback patterns.
