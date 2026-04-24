# Change: Add global Codex context hooks dispatcher

Multica issue: INT-334

## Why

Agents currently spend tokens rediscovering whether they are running on the dev or prod backend checkout, and repo-local instructions duplicate machine/path checks. For `/int/data` and `/int/punkt-b`, the machine and path define strict contour rules:

- dev work happens on `agents@vds.intdata.pro:/int/data`;
- prod checkout is `agents@vds.punkt-b.pro:/int/punkt-b`;
- backend edits flow through dev -> `origin/main` -> prod refresh;
- direct prod agent commits/pushes are not allowed.

This contour context should be injected by Codex hooks before the agent chooses commands, not repeatedly re-derived by every task.

## What Changes

- Add a repo-owned Codex hooks dispatcher under `/int/tools/codex/hooks`.
- Install a minimal `~/.codex/hooks.json` on both VDS hosts pointing to the dispatcher.
- Enable `features.codex_hooks` on the prod VDS as it is already enabled on dev.
- Inject contour context at session/prompt time for managed repos.
- Block unsafe mutating git commands on the prod checkout and wrong-host/wrong-path managed contour commands.
- Record lightweight hook events under `/int/tools/.runtime/codex-hooks/`.

## Scope Boundaries

- No database, migration, Supabase runtime, or production service changes.
- No direct product code changes in `/int/data` or `/int/punkt-b`.
- Codex home changes are limited to the documented hook config file and feature flag explicitly requested by the owner.

## Acceptance

- `codex exec` from `/int/data` receives injected dev contour context.
- `codex exec` from `/int/punkt-b` receives injected prod contour context.
- A simulated or live `git commit`/mutating git command is blocked on prod.
- Dev `/int/data` still allows normal read-only commands and does not block legitimate dev commands.
- Hook source is tracked in `/int/tools`; runtime logs stay ignored under `/int/tools/.runtime`.
