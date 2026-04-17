# Design: IntData Tools ops console plugins

## Architecture

The implementation uses separate Codex plugin packages for UX/install boundaries and one shared MCP helper for CLI-backed tools:

- Plugin manifests live under `codex/plugins/<plugin>/`.
- Profile launchers live under `codex/bin/mcp-<plugin>.cmd` and `.sh`.
- `codex/bin/mcp-intdata-cli.py` implements the JSON-RPC MCP server and dispatches by `--profile`.

## Guard model

Read commands run directly. Mutating or runtime-control commands must include:

- `confirm_mutation: true`
- `issue_context` matching `INT-*`

The wrapper never accepts shell strings. It accepts command enums plus structured `args: string[]` and runs subprocesses with `shell=False`.

## Boundaries

The wrapper is an adapter only. Canonical behavior stays in existing CLIs:

- OpenSpec CLI through `codex/bin/openspec.ps1` or `codex/bin/openspec`.
- Multica CLI through `multica`.
- Routing through `codex/bin/agent_tool_routing.py`.
- Delivery through `scripts/codex/int_git_sync_gate.py` and `delivery/bin/publish_*.py`.
- Existing subsystem CLIs for intdb, gatesctl, host, SSH, vault, browser and connectors.
