# Change: Consolidate IntData ops plugins into governance/runtime

## Why

The current `IntData Tools` plugin catalog exposes six narrowly-scoped ops plugins for routing/delivery/gates and host/ssh/browser runtime flows. This duplicates operator mental overhead and inflates plugin management in Codex App.

## What Changes

- Replace six plugin IDs with two aggregated plugins:
  - `intdata-governance`
  - `intdata-runtime`
- Perform a hard cutover with no alias compatibility for removed plugin IDs/tool names.
- Keep existing mutation guards (`confirm_mutation=true`, `issue_context=INT-*`) for mutating tools.
- Update local Codex plugin enablement config to use the two new plugin IDs.

## Scope

- Marketplace metadata, packaged plugins, launcher scripts, shared MCP wrapper surface, README docs, and local `C:\Users\intData\.codex\config.toml`.
- Canonical backend engines remain unchanged (routing, delivery, gatesctl, host, ssh, browser launchers).
