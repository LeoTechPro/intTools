# Design: Governance/Runtime plugin consolidation

## Architecture

- Keep one shared executable wrapper (`codex/bin/mcp-intdata-cli.py`).
- Replace profile fan-out:
  - remove: `intdata-routing`, `intdata-delivery`, `gatesctl`, `intdata-host`, `intdata-ssh`, `intdata-browser`
  - add: `intdata-governance`, `intdata-runtime`

## Tool contracts

### `intdata-governance`
- `routing_validate`
- `routing_resolve`
- `sync_gate`
- `publish`
- `gate_status`
- `gate_receipt`
- `commit_binding`

### `intdata-runtime`
- `host_preflight`
- `host_verify`
- `host_bootstrap`
- `recovery_bundle`
- `ssh_resolve`
- `ssh_host`
- `firefox-devtools-testing` workflow (`browser_profile_launch` remains deprecated compatibility)

## Guard model

- Mutating operations remain blocked unless:
  - `confirm_mutation=true`
  - `issue_context` matches `INT-*`
- Read-only operations stay callable without mutation confirmation.

## Migration behavior

- Hard-breaking migration:
  - removed plugin IDs and old tool names are not kept as aliases.
  - marketplace/UI surface shows only new plugin IDs.
