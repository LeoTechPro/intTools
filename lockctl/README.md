# lockctl

`lockctl` is a public first-party CLI for scoped file lease coordination.

It prevents concurrent agents or operators from editing the same repo-relative file without a visible lease. It is not a review system, gate ledger, or issue tracker.

## Install

Use the wrapper that fits your platform:

```powershell
pwsh -File D:\int\tools\lockctl\install_lockctl.ps1
```

```bash
bash /int/tools/lockctl/install_lockctl.sh
```

The implementation entrypoint is `lockctl.py`; shell wrappers are convenience launchers.

## Runtime State

`LOCKCTL_STATE_DIR` controls where runtime state is stored.

If unset, existing intData deployments may default to `/int/tools/.runtime/lockctl` or `D:\int\tools\.runtime\lockctl` for compatibility. Packaged installs should set an explicit state directory outside source control.

Runtime files are not public source:

- `locks.sqlite`
- `events.jsonl`

## CLI Contract

Common commands:

```bash
lockctl acquire --repo-root . --path README.md --owner agent:local --reason "docs update" --lease-sec 60 --format json
lockctl status --repo-root . --path README.md --format json
lockctl release-path --repo-root . --path README.md --owner agent:local --format json
lockctl gc --format json
```

One active writer lease is allowed per repo-relative file. `issue` metadata is optional.

## Tests

```powershell
python -m unittest discover -s D:\int\tools\lockctl\tests
```
