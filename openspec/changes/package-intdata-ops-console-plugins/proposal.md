# Change: Package IntData Tools ops console plugins

## Why

`IntData Tools` now exposes `lockctl` and `intbrain` as packaged Codex plugins, but other core `/int/tools` capabilities are still only discoverable as scripts, project overlays, or CLI commands. This makes Codex App plugin installation incomplete and leaves ops workflows split across ad-hoc entrypoints.

## What Changes

- Add packaged Codex plugins for OpenSpec, Multica, routing, delivery, intdb, gatesctl, browser profiles, host tooling, SSH diagnostics, vault tooling, and PunktB connectors.
- Add a shared structured MCP subprocess wrapper for these CLI-backed plugins.
- Require mutation guards for write/control commands: `confirm_mutation=true` and `issue_context=INT-*`.
- Register all new plugins in the `IntData Tools` marketplace as `INSTALLED_BY_DEFAULT` + `ON_INSTALL`.

## Scope boundaries

- Scope is limited to repo-owned plugin packaging, MCP wrappers, marketplace metadata, OpenSpec change package, and README documentation.
- Existing CLI engines remain canonical; wrappers do not replace their implementations.
- External Codex App local plugin cleanup outside `/int` is not part of this change.
- Runtime secrets remain outside git.

## Acceptance

- Every new plugin has a tracked `.codex-plugin/plugin.json`, `.mcp.json`, and skill pointer.
- Every plugin MCP server responds to `initialize` and `tools/list`.
- OpenSpec and Multica mutation guards reject write/control commands without explicit confirmation and `INT-*` issue context.
- JSON manifests validate and routing registry validation remains green.
