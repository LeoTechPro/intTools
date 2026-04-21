# Change: Remove intData Control Multica Surface (INT-255)

## Why

The local `intdata-control` Multica MCP wrapper duplicates the official Multica interface and adds extra routing/ping overhead. Agents should use documented native Multica paths instead of a repo-owned proxy layer.

## What Changes

- Remove all `multica_*` tools from the `intdata-control` MCP surface.
- Remove repo-owned Multica capability skills from the `intdata-control` plugin.
- Update verifier, docs, and packaged skills so `intdata-control` no longer claims Multica ownership.
- Document official `multica` CLI as the baseline agent path, with official `mcp__multica__` allowed only when installed by the runtime.

## Scope Boundaries

- Multica remains the task-control-plane for agent work.
- This change does not remove the `multica` CLI or change Multica server/runtime behavior.
- This change does not mutate live Codex home; only repo-owned plugin/skill source is updated.

## Issue

Owning Multica issue: `INT-255`.
