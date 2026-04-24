# Remove Local Delivery Publish Surface

## Summary

Remove the repo-owned `delivery/bin/publish_*` publish/deploy wrappers and the legacy `codex/bin/publish_*.ps1` shims. Agents should use explicit native `git` and deployment commands under owner direction instead of a hidden local publish abstraction that can drift from real operational needs.

## Scope

- Issue: `INT-258`
- Repo: `/int/tools`
- Mode: `SPEC-MUTATION -> EXECUTE -> FINISH`
- Domain: `ops-tooling / delivery / MCP plugin surface / docs / routing`

## Motivation

The local publish contour hides branch, push, host, and deploy assumptions inside repo-owned wrappers. That makes stale publication behavior easy to forget and hard to audit. The owner explicitly requested less hidden machinery and removal of `publish_repo.py` plus its wrappers.

## Changes

- Delete `delivery/bin/publish_repo.py` and repo-specific `delivery/bin/publish_*` wrappers.
- Delete legacy `codex/bin/publish_repo.ps1` and `codex/bin/publish_data.ps1` compatibility shims.
- Remove the `publish` tool from the `intdata-control` MCP surface.
- Remove publish/deploy capabilities from the high-risk routing registry.
- Remove publish wrapper smoke from the pre-push hook.
- Update docs, skills, and active OpenSpec deltas so `sync_gate` remains the governed repository synchronization path and publish/deploy wrappers are no longer documented as canonical.

## Non-Goals

- Superseded by `remove-local-sync-gate-and-codex-home-mutation`: `codex/scripts/int_git_sync_gate.py` is removed.
- Do not create a replacement publish wrapper.
- Do not mutate live `C:\Users\intData\.codex`.
- Do not push or deploy other repos.
