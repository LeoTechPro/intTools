# Change: Link OpenSpec changes to Multica issues (INT-223)

## Why

`/int/tools` already requires OpenSpec for tracked tooling/process mutations and
Multica Issues for agent execution. The two systems need an explicit linkage so
requirements and execution history stay connected without duplicating OpenSpec
content into issue bodies.

## What Changes

- Require every tracked tooling/process OpenSpec change in `/int/tools` to name
  its Multica `INT-*` issue.
- Require the Multica issue/worklog to name the relevant OpenSpec change path.
- Keep OpenSpec as source-of-truth for requirements/spec/acceptance.
- Keep Multica as source-of-truth for execution status, worklog, blockers, and
  closure.
- Forbid full OpenSpec mirroring into Multica; issue comments should carry only
  short summaries and links/paths.

## Out of Scope

- Runtime enforcement, schema changes, or new CLI/API checks.
- Rewriting historical OpenSpec packages.
- Changing the already completed runtime-root change package.

## Acceptance

- Canonical process spec documents the OpenSpec `<->` Multica linkage contract.
- Repo governance docs include the same rule and a short linkage template.
- `INT-223` contains a comment linking to this OpenSpec change.
