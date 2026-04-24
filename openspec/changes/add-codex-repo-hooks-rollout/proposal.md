# Change: Add repo-local Codex hooks rollout

## Why

Codex hooks are now available in the local Windows CLI build and already work on Linux VDS hosts. The intTools repo needs versioned, repo-local hook policy instead of ad-hoc global dispatchers or mutable Codex home overlays.

## What Changes

- Add `.codex/hooks.json` and a repo-local contour guard for `/int/tools`.
- Treat `D:\int\tools` as the Windows source checkout and VDS `/int/tools` checkouts as read-only mirrors refreshed from `origin/main`.
- Add a `commit-msg` git hook that requires `INT-*` and the Codex co-author trailer.

## Scope

- This change only covers repo-local Codex/git hook policy for `/int/tools`.
- It does not reintroduce a global dispatcher and does not mutate `~/.codex` / `C:\Users\intData\.codex`.
