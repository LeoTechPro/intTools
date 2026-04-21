# Design

## Lockctl Boundary

`lockctl/lockctl_core.py` remains the canonical engine. Platform entrypoints (`lockctl.py`, `lockctl`, `lockctl.ps1`, `lockctl.cmd`) keep the same command names and argument semantics across Linux, macOS, and Windows.

MCP exposure is through the shared `codex/bin/mcp-intdata-cli.py --profile intdata-control` runtime. Separate `mcp-lockctl.*` wrappers are legacy and must not be referenced as active entrypoints.

## Git Synchronization

`int_git_sync_gate` is removed. Agents and operators use explicit native git commands:

- `git status --short --branch`
- `git fetch --prune origin`
- `git pull --ff-only` only on a clean checkout when an upstream is configured and behind
- `git push origin main:main` with `ALLOW_MAIN_PUSH=1` when owner-approved publication targets `main`

The repo pre-push hook remains the guardrail for env-file policy and `main` push confirmation.

## Codex Home

Repo-owned scripts must not copy, mirror, patch, delete, compare, or enforce internal files under Codex home. Host bootstrap may create repo-local runtime directories under `/int/tools/.runtime/**`; host verification checks repo/runtime prerequisites only.

Tracked `codex/assets/codex-home/**` content is not an active sync source and must not be wired into an automated install/sync path.

## Multica Autopilot Sidecar

The sidecar mixed useful report formatting with hidden side effects: Multica comments, Probe outbox enqueue, dedupe state, hardcoded defaults, and non-dry-run default behavior. Its report can be reproduced explicitly with official `multica` CLI reads, so the repo-owned sidecar is removed instead of hardened.
