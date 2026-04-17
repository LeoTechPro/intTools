# Change: Publish Cabinet and MemPalace in IntData Tools (INT-6)

## Why

`cabinet` and `mempalace` are enabled in user runtime config, but they are not published through the repo-owned `IntData Tools` catalog (`.agents/plugins/marketplace.json` + `codex/plugins/*`). Because of this, Codex App does not show them in the `IntData Tools` family filter and local/VDS checkouts drift.

## What Changes

- Add `cabinet` and `mempalace` to `.agents/plugins/marketplace.json` with `INSTALLED_BY_DEFAULT` + `ON_INSTALL`.
- Add tracked packaged plugins:
  - `codex/plugins/cabinet/.codex-plugin/plugin.json`
  - `codex/plugins/cabinet/.mcp.json`
  - `codex/plugins/mempalace/.codex-plugin/plugin.json`
  - `codex/plugins/mempalace/.mcp.json`
- Update README plugin catalog section so documentation matches the published family.
- Sync `/int/tools` to `vds.intdata.pro` after local validation to remove catalog drift.

## Scope Boundaries

- Scope is limited to plugin packaging/catalog documentation and OpenSpec lifecycle artifacts in `/int/tools`.
- No change to `mcp-intdata-cli` profile surface in this change.
- No change to Supabase roles, runtime secret locations, or unrelated plugins.

## Acceptance

- `cabinet` and `mempalace` are visible entries in `IntData Tools` catalog source (`.agents/plugins/marketplace.json`).
- Both plugin package manifests and `.mcp.json` files are tracked under `codex/plugins/<plugin>/`.
- JSON manifests validate and local MCP smoke (`initialize` + `tools/list`) passes for both plugin servers.
- Local and VDS `/int/tools` checkouts contain the same plugin catalog entries and package directories for `cabinet` and `mempalace`.
