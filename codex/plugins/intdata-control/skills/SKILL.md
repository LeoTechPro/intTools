---
name: intdata-control
description: intData Control tools for lockctl, Multica, OpenSpec, routing, gates, commit binding, sync gates, and publication.
---

# intData Control

Use the `intdata-control` plugin for governed `/int/tools` control-plane work:
locks, Multica issues, OpenSpec lifecycle, routing validation, sync gates,
publication, gate receipts, and commit binding.

## Capability skills

- `intdata-control-lockctl`: file locks and lock cleanup.
- `intdata-control-openspec-read`: read-only OpenSpec discovery and validation.
- `intdata-control-openspec-mutation`: OpenSpec lifecycle mutations.
- `intdata-control-multica`: issue/worklog/project/runtime coordination.
- `intdata-control-routing`: high-risk routing registry validation and resolve.
- `intdata-control-sync-gate-publish`: sync gate and publication flows.
- `intdata-control-gate-receipts-commit-binding`: gate receipts and commit binding.

## Rules

- Keep OpenSpec as requirements/spec/acceptance source-of-truth.
- Keep Multica as execution/worklog/status/blockers/closure source-of-truth.
- Use full `INT-*` issue identifiers for issue-bound mutations.
- Mutating tools require explicit mutation context unless the runtime is running
  in owner-approved YOLO mode.
- Do not fall back to removed plugin IDs `lockctl`, `multica`, `openspec`, or
  `intdata-governance`.
- If a task touches files in `/int/tools`, use the lockctl skill before editing.
