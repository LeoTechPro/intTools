# Change: Move governance state under intTools runtime

Multica issue: INT-235

## Why

`lockctl` and `gatesctl` currently default to Codex memory paths under `~/.codex/memories`. These are intTools governance runtimes, not Codex memories, and they must stay machine-local so shared Codex memory can move to `/2brain/.codex/memories` without syncing SQLite/events for locks and gates.

## What Changes

- Default `lockctl` state moves to `/int/tools/.runtime/lockctl`.
- Default `gatesctl` state moves to `/int/tools/.runtime/gatesctl`.
- `LOCKCTL_STATE_DIR` and `GATESCTL_STATE_DIR` remain explicit overrides.
- Old `.codex/memories/{lockctl,gatesctl}` paths become non-destructive migration sources only.
- Docs mark `/int/tools/.runtime/**` as the canonical ignored host-runtime for these governance states on local Windows and `vds.intdata.pro`.

## Scope

- Runtime state resolution in `lockctl` and `gatesctl`.
- Targeted tests and documentation.
- No Codex memories relocation in this change.
