# Change: Require plugin-first access for agent governance tools

## Why

Agents currently may treat missing `openspec` or `multica` binaries in `PATH` as a reason to call repo-local wrappers directly. That bypasses the intended MCP plugin surface and weakens mutation guards, issue-context checks, and auditability.

For `/int/tools`, OpenSpec and Multica are governed control-plane tools. In Codex/OpenClaw runtimes where the MCP plugins are installed, agents must use the plugin tools first. Repo-local CLI wrappers still exist, but they are operator/adapter entrypoints and explicit fallback paths, not the normal agent interface.

## What Changes

- Add process requirements that make MCP plugin access the primary agent path for OpenSpec and Multica.
- Clarify that direct `openspec`, `multica`, and repo-local wrapper calls are allowed only when the matching MCP plugin is unavailable or blocked and the owner approves the fallback.
- Fix `lockctl` issue metadata so locks can be taken without issue context and full Multica identifiers such as `INT-224` are accepted when issue metadata is provided.
- Update repo instructions and packaged skills so agents do not cite Windows `PATH` issues as a reason to bypass `mcp__openspec__` or `mcp__multica__`.
- Keep existing CLI wrappers documented as versioned operator/adapter compatibility entrypoints.

## Scope boundaries

- Scope is limited to `/int/tools` governance docs, OpenSpec process delta, and Codex managed skill/plugin instructions.
- Scope includes the narrow `lockctl` validation fix for optional/full issue identifiers.
- This change does not remove OpenSpec or Multica CLI wrappers.
- This change does not modify OpenSpec or Multica runtime implementations.
- Existing unrelated untracked OpenSpec work remains out of scope.

## Acceptance

- Agents are explicitly instructed to use `mcp__openspec__` for OpenSpec list/show/status/validate/lifecycle operations when available.
- Agents are explicitly instructed to use `mcp__multica__` for Multica issue operations when available.
- Direct CLI/wrapper fallback requires a recorded plugin attempt, blocker/error, and explicit owner approval.
- `lockctl` can acquire/status locks without issue metadata, and accepts full `INT-*` issue ids when metadata is provided.
- The OpenSpec change validates strictly.
