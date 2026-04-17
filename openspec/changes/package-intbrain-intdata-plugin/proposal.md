# Change: Package IntBrain as IntData Tools Codex plugin

## Why

`IntBrain` is currently available as MCP launchers under `codex/bin/`, while `lockctl` is exposed as a packaged Codex plugin through the `IntData Tools` marketplace. This creates inconsistent installation and discovery behavior in Codex App.

## What Changes

- Add a packaged `intbrain` Codex plugin under `codex/plugins/intbrain`.
- Add a Windows `mcp-intbrain.cmd` launcher for Codex App runtime.
- Register `intbrain` in the `IntData Tools` marketplace.
- Set every `IntData Tools` marketplace entry to `INSTALLED_BY_DEFAULT` with `ON_INSTALL` authentication.
- Keep IntBrain secrets in external runtime env files or inherited process env.

## Scope boundaries

- Scope is limited to `/int/tools` Codex plugin packaging, launcher wiring, marketplace metadata, and docs.
- IntBrain API behavior and MCP tool schemas are not changed.
- External Codex App local plugin state outside `/int` is not modified in this change.

## Acceptance

- `IntBrain` appears as an `IntData Tools` catalog plugin package.
- `lockctl` and `intbrain` marketplace entries use `INSTALLED_BY_DEFAULT` + `ON_INSTALL`.
- Windows launcher starts the existing Python MCP server and reports missing auth env clearly.
- JSON manifests validate.
