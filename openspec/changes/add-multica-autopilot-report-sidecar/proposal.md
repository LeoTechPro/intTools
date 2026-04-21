# Change: Add Multica autopilot report sidecar

Status note: superseded by `remove-local-sync-gate-and-codex-home-mutation`. The repo-owned sidecar was removed/forbidden because it mixed report formatting with hidden Multica comments, Probe outbox delivery, dedupe state, and hardcoded defaults. Use explicit official `multica` CLI reads for hygiene reports instead.

## Why

Multica autopilots currently create new issues for scheduled hygiene reports. That makes useful audits harder to read because each run becomes another issue. The desired flow is to keep report history in a configured master issue and notify the owner through the existing Probe/Nexus Telegram delivery contour.

## What Changes

- Removed/forbidden: a repo-owned sidecar under `delivery/bin/` for deterministic Multica autopilot report delivery.
- The sidecar reads Multica issues and issue runs through existing Multica CLI commands.
- The sidecar writes report output to configured master issues through `multica issue comment add`.
- Telegram copies are enqueued through the existing Probe outbox CLI boundary, not direct Probe imports and not direct Telegram calls.
- Removed/forbidden runtime mapping through `AUTOPILOT_REPORT_TARGETS`; explicit `multica` CLI reads replace this sidecar.
- Missing target mapping fails closed and never creates a Multica issue.

## Scope boundaries

- Multica application code and database schema are not changed.
- Probe/Nexus contracts are reused as-is.
- OpenClaw remains a fallback for LLM-based analysis only and is not required for deterministic delivery.
- Runtime state and secrets remain outside the `/int/tools` repository.

## Acceptance

- A dry-run can generate a hygiene report without creating issues, comments, or Telegram outbox rows.
- A configured run posts one comment to the configured master issue and enqueues one Probe outbox row.
- Re-running the same dedupe key does not duplicate the comment or outbox row.
- If Multica comment creation fails, Telegram enqueue is skipped.
- If Probe enqueue fails after a comment is posted, the state records comment success and delivery failure for retry.
