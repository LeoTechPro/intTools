# Change: Remove PunktB connectors plugin from IntData Tools

## Why

The owner requested removing the optional PunktB connectors plugin from the IntData Tools marketplace. The connector bundle is project-specific and should not appear as an installable default IntData Tools plugin.

## What Changes

- Remove `punktb-connectors` from `.agents/plugins/marketplace.json`.
- Remove the packaged plugin source under `codex/plugins/punktb-connectors`.
- Remove the `mcp-punktb-connectors` launchers.
- Remove the `punktb-connectors` profile from the shared MCP wrapper.
- Keep underlying connector scripts untouched; this change removes only the Codex plugin package and marketplace exposure.

## Impact

- Codex App should no longer show `PunktB Connectors` under `IntData Tools` after marketplace/config refresh.
- Existing core IntData Tools plugins are unchanged.
