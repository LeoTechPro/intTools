# lockctl

`lockctl` is the machine-local writer-lock runtime for Codex/OpenClaw on this host.

## Shell UX

Use the public shell entrypoint:

```bash
lockctl
lockctl --help
lockctl help acquire
man lockctl
```

Bare `lockctl` prints the top-level help and exits successfully.

## Runtime model

- One active writer lease per repo-relative file.
- Truth for active locks lives in SQLite, not in project-local YAML files.
- Leases are short-lived and must be renewed while a write is active.
- `release-path` is the normal per-file cleanup path.
- `release-issue` is the normal bulk cleanup path for issue-bound repos.

Runtime files:

- `LOCKCTL_STATE_DIR=/home/leon/.codex/memories/lockctl`
- SQLite: `/home/leon/.codex/memories/lockctl/locks.sqlite`
- Event log: `/home/leon/.codex/memories/lockctl/events.jsonl`

## Common examples

```bash
lockctl acquire \
  --repo-root /git/punctb \
  --path README.md \
  --owner codex:session-1 \
  --issue 1217 \
  --lease-sec 60 \
  --format json

lockctl status --repo-root /git/punctb --issue 1217 --format json

lockctl release-path \
  --repo-root /git/punctb \
  --path README.md \
  --owner codex:session-1 \
  --format json

lockctl release-issue --repo-root /git/punctb --issue 1217 --format json

lockctl gc --format json
```

## Notes

- Do not edit SQLite or `events.jsonl` directly.
- `punctb` and `intdata` now treat `lockctl` as the runtime source of truth for active file locks.
