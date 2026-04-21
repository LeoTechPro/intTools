# Change: Remove local sync gate and Codex-home mutation paths

Owning Multica issue: `INT-260`

## Why

`int_git_sync_gate` duplicates native git behavior behind a repo-owned wrapper and now carries more maintenance risk than value. The repo also still contains old Codex-home overlay/sync paths that are retired but remain discoverable enough to be reactivated accidentally.

`lockctl` is different: it is still a required machine-local writer-lock runtime. It should remain a repo-owned core with the same CLI command surface on Linux and Windows, plus an MCP surface through `intdata-control` and plugin skills.

The Multica autopilot report sidecar has narrow value as a hygiene-report formatter, but its production mode writes Multica comments and Probe outbox messages, uses hardcoded defaults, and can become stale silently. This should be removed instead of preserved as hidden automation.

## What Changes

- Remove `int_git_sync_gate` engines/adapters/tests and the `sync_gate_*` MCP tools.
- Remove sync-gate capability routing and documentation as a required `/int/tools` process step.
- Keep native git commands as the explicit publication path, with existing hooks and `ALLOW_MAIN_PUSH=1` for main pushes.
- Remove Codex-home sync/detach scripts and dead bootstrap code that can copy/remove content under Codex home.
- Make host bootstrap/verify treat Codex home as Codex-owned state and avoid inspecting or mutating its internal layout.
- Preserve `lockctl` CLI and `intdata-control` MCP tools, and repair stale `mcp-lockctl.*` references to the current `mcp-intdata-cli --profile intdata-control` surface.
- Remove `multica_autopilot_report_sidecar.py` and its tests/docs.

## Out of Scope

- Removing `lockctl` core, CLI wrappers, MCP tools, or plugin lockctl skills.
- Mutating live `C:\Users\intData\.codex` or any other Codex home directory.
- Replacing native git, native Codex plugin/skill mechanisms, or official Multica CLI.

## Acceptance

- `intdata-control` exposes no `sync_gate_*`, no `publish`, and no `multica_*` tools.
- `lockctl` CLI wrappers and MCP tools remain available.
- Active docs do not instruct agents to run `int_git_sync_gate` or repo scripts that mutate Codex home.
- Host bootstrap/verify do not write, mirror, or validate internal Codex home overlays.
- `multica_autopilot_report_sidecar.py` and its test are gone.
- Verifiers/tests reject stale `int_git_sync_gate`, `mcp-lockctl.*`, and autopilot sidecar references in active docs/skills.
