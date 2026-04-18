# Change: Harden int-tools plugin and app surfaces

## Why

`intbrain`, `intdata-control`, `intdata-runtime`, and `intdb` are packaged as Codex plugins and expose MCP tools, but agents still need sharper capability-level skills and reproducible verification before the surfaces can be treated as working app/plugin infrastructure.

## What Changes

- Add capability skills for every int-tools MCP tool group.
- Add app-surface metadata to plugin manifests without inventing an unsupported `.app.json` schema.
- Add a repo-owned verifier for manifests, MCP protocol smoke, tool counts, skill coverage, and mutation guards.
- Document the internal remote ChatGPT Apps/Connectors v1 shape as a tool-only MCP app.
- Add missing mutation guards for IntBrain write/import tools.

## Scope boundaries

- Existing CLI engines and product APIs remain canonical.
- Local Codex plugins stay repo-owned distribution/UX surfaces.
- Remote ChatGPT app v1 is documented and testable as a design target, not deployed in this change.
- Runtime secrets stay outside git.

## Issue

Owning Multica issue: `INT-226`.

## Acceptance

- All four plugin manifests parse and include discovery metadata.
- Every plugin MCP profile responds to `initialize`, `ping`, and `tools/list`.
- Tool counts remain `intbrain=29`, `intdata-control=35`, `intdata-runtime=9`, `intdb=1`.
- Every MCP tool is assigned to exactly one capability skill.
- High-risk guarded tools reject missing `confirm_mutation=true` and `issue_context=INT-*`.
- OpenSpec validation and routing validation pass.
