# Change: Unify int-tools plugins on shared MCP runtime and intData branding

## Why

The active `int-tools` catalog still mixes a shared MCP runtime with standalone wrappers for `lockctl` and `intbrain`, while plugin UI branding is inconsistent (`IntData`, `intdb`, `lockctl`, `IntBrain`). This increases maintenance and confuses plugin identity in Codex UI.

## What Changes

- Move all 8 active `int-tools` plugins to one launcher/runtime pair:
  - `codex/bin/mcp-intdata-cli.py`
  - `codex/bin/mcp-intdata-cli.cmd|.sh`
- Port `lockctl` and `intbrain` profiles into `mcp-intdata-cli.py` without changing public tool names/contracts.
- Remove legacy dedicated wrappers/runtimes for all 8 plugins.
- Repoint each plugin `.mcp.json` to the shared launcher + `--profile <plugin-id>`.
- Apply unified catalog branding:
  - Family: `intData Tools`
  - `lockctl` UI name: `intData Locks`
  - `intbrain` UI name: `intData Brain`
  - `intdb` UI name: `intData DBA`
  - `intdata-governance/runtime/vault` recased to `intData ...`
  - `Multica` and `OpenSpec` remain unchanged.

## Scope

- `codex/bin`, `codex/plugins/*/.mcp.json`, plugin `plugin.json` interface fields, marketplace family display name, routing/layout policy, AGENTS/README references, and OpenSpec artifacts for this rollout.
