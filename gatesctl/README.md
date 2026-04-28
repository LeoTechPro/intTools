# gatesctl

`gatesctl` is a public first-party CLI for gate receipts, approvals, and commit binding.

It records verifiable gate evidence for issue-bound workflows. It does not replace `lockctl`; file leases and gate receipts are separate concerns.

## Runtime State

`GATESCTL_STATE_DIR` controls where runtime state is stored.

If unset, existing intData deployments may default to `/int/tools/.runtime/gatesctl` or `D:\int\tools\.runtime\gatesctl` for compatibility. Packaged installs should set an explicit state directory outside source control.

Runtime files are not public source:

- `gates.sqlite`
- `events.jsonl`

## CLI Contract

Common commands:

```bash
gatesctl plan-scope --repo-root . --issue INT-000 --files README.md
gatesctl approve --repo-root . --issue INT-000 --gate docs --decision approve --actor owner --role reviewer --files README.md
gatesctl verify --repo-root . --issue INT-000 --stage commit --files README.md
gatesctl bind-commit --repo-root . --commit-sha HEAD
```

Server-side hook samples are templates for self-hosted remotes only. GitHub.com does not support installing these hooks directly.

## Tests

```powershell
python -m unittest discover -s D:\int\tools\gatesctl\tests
```
