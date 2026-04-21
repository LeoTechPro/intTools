# Change: Route `/int/data` dev backend work to agents host

Multica issue: INT-243

## Why

The local Windows checkout `D:\int\data` is being removed. Active instructions and tooling must not keep sending agents to that path for intdata dev backend work, because the canonical working checkout now lives on `agents@vds.intdata.pro:/int/data`.

## What Changes

- Remove the hardcoded `D:\int\data` default from guarded `intdb` migration entrypoints.
- Keep explicit local repo support for intentional disposable/local flows via `--repo` or `INTDB_DATA_REPO`.
- On Windows, stop auto-discovering sibling `D:\int\data`; route dev backend work to `agents@vds.intdata.pro:/int/data`.
- Update active docs/agent instructions that reference the local checkout as an operational path.

## Scope Boundaries

- No backend schema, migration, or runtime DB changes.
- No cleanup of historical evidence docs unless they are active operational instructions.
- No Codex home changes.

## Acceptance

- `D:\int\data` is removed from this machine.
- Active intdb docs/skills/AGENTS no longer point dev backend work at local `D:\int\data`.
- Windows `intdb` auto-discovery does not silently use sibling `D:\int\data`.
- Remote checkout `agents@vds.intdata.pro:/int/data` is reachable.
