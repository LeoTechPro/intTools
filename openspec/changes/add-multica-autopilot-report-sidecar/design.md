# Design: Multica autopilot report sidecar

Status note: superseded by `remove-local-sync-gate-and-codex-home-mutation`; this sidecar is removed/forbidden.

## Runtime boundary

The sidecar lives in `/int/tools/delivery/bin` as machine-wide delivery tooling. It does not import code from Multica, Probe, or Nexus. Integration happens only through existing command/API boundaries:

- Multica CLI for issue listing, run history, and comments.
- Probe `probe_outbox_enqueue.py` CLI for Telegram outbox enqueue.

## Delivery flow

1. Removed/forbidden behavior: resolve target mapping from `AUTOPILOT_REPORT_TARGETS` and `--target`.
2. Fail closed if a requested autopilot has no configured master issue.
3. Collect active issues and recent run history through Multica CLI.
4. Render a deterministic Markdown hygiene report.
5. Add the report as a comment to the configured master issue.
6. Enqueue a Telegram copy into Probe outbox.
7. Persist phase state in an external JSON file so retries do not duplicate already completed phases.

## Dedupe model

The dedupe key is `multica-autopilot:<autopilot_id>:<period_key>` unless explicitly overridden. State records comment and Telegram phases separately:

- comment posted, Telegram not enqueued: retry Telegram only.
- both phases completed: no-op.
- comment failed: no Telegram enqueue.

## Failure policy

Missing target mapping, unreadable Multica data, or invalid runtime config is a hard failure. The sidecar never creates a new Multica issue as fallback.
