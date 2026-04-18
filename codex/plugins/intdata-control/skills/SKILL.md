---
name: intdata-control
description: intData Control tools for lockctl, Multica, OpenSpec, routing, gates, commit binding, sync gates, and publication.
---

# intData Control

Use the `intdata-control` plugin for governed `/int/tools` control-plane work:
locks, Multica issues, OpenSpec lifecycle, routing validation, sync gates,
publication, gate receipts, and commit binding.

## Rules

- Keep OpenSpec as requirements/spec/acceptance source-of-truth.
- Keep Multica as execution/worklog/status/blockers/closure source-of-truth.
- Use full `INT-*` issue identifiers for issue-bound mutations.
- Mutating tools require explicit mutation context unless the runtime is running
  in owner-approved YOLO mode.
- Do not fall back to removed plugin IDs `lockctl`, `multica`, `openspec`, or
  `intdata-governance`.
