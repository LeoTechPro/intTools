# Change: Move intTools runtime under tools checkout

## Why

The local runtime currently lives at `/int/.runtime` while all real owners and consumers are in the `/int/tools` ops-tooling contour. This makes the runtime easy to forget when launching from the project checkout and keeps secrets/browser state outside the contour that documents and manages them.

## What Changes

- Move the canonical intTools runtime root to `/int/tools/.runtime`.
- Add `.runtime/` to the intTools gitignore policy so local state and secrets remain untracked.
- Update Codex/OpenClaw wrappers, docs, tests, and service templates to use `/int/tools/.runtime` by default.
- Keep `/int/.runtime` only as a local compatibility junction/fallback during transition.

## Scope

- `/int/tools` tracked docs, wrappers, tests, and OpenSpec process delta.
- Local runtime migration from `D:\int\.runtime` to `D:\int\tools\.runtime`.
