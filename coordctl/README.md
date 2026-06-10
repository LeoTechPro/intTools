# coordctl

`coordctl` is a parallel, Git-aware coordination utility for multi-agent edits.

It replaces `lockctl`, which has been fully retired and removed from the repository;
its runtime history was imported into coordctl via `import_lockctl_history.py`.

## Runtime State

Runtime state is stored outside source control:

- default: `D:\int\tools\.runtime\coordctl` or `/int/tools/.runtime/coordctl`
- override: `COORDCTL_STATE_DIR`

Runtime files:

- `coord.sqlite`
- `events.jsonl`

## Install

`bash coordctl/install_coordctl.sh` (Linux/macOS; honours `COORDCTL_INSTALL_BIN`,
default `~/.local/bin`) or `coordctl/install_coordctl.ps1` (Windows). The standard
`codex/tools/install_tools.*` pipeline installs coordctl automatically. Set a stable
owner id for provenance: `export COORDCTL_OWNER="<agent>:<task|INT-*>"`.

## CLI

```bash
coordctl begin --owner codex:session --format json   # cheap non-blocking start; autodetects repo/branch/base
coordctl begin --owner codex:session --path README.md --format json   # also records a coarse file intent
coordctl session-start --repo-root /int/tools --owner codex:session --branch agent/INT-1/a --base main --format json
coordctl intent-acquire --repo-root /int/tools --path README.md --owner codex:session --base main --region-kind hunk --region-id 12:18 --lease-sec 3600 --format json
coordctl status --repo-root /int/tools --format json
coordctl status --repo-root /int/tools --brief --format json   # compact: counts + active owners/paths
coordctl commit-scope-report --repo-root /int/tools --format json   # advisory, never fails
coordctl commit-scope-check --repo-root /int/tools --format json    # gate: fails only on unmerged/partial-file
coordctl heartbeat --session-id <session-id> --format json
coordctl merge-dry-run --repo-root /int/tools --target main --branch agent/INT-1/a --format json
coordctl release --session-id <session-id> --format json
coordctl release --repo-root /int/tools --lease-id <lease-id> --format json    # release one orphan/legacy lease
coordctl release --repo-root /int/tools --owner codex:session --format json    # release one owner's leases
coordctl release --repo-root /int/tools --path README.md --format json         # release leases on a path
coordctl cleanup --session-id <session-id> --final-state released --dry-run --format json
coordctl cleanup --session-id <session-id> --final-state merged --delete-worktree --delete-branch --apply --format json
coordctl gc --dry-run --format json
coordctl gc --rotate-events --dry-run --format json    # preview journal rotation + runtime sizes
coordctl gc --rotate-events --apply --format json       # archive events.jsonl into state-dir archive/ (coord_events preserved)
```

## Region Model v1

- `file`: coarse fallback for files that cannot be safely split.
- `hunk`: MVP coordination unit, identified by a base-file line range such as `12:18`.
- `symbol`, `json_path`, and `section`: reserved for future semantic extractors and rejected in v1.

Conflict detection is advisory and non-blocking: recording an intent always succeeds.
An overlapping active lease from another owner is returned as a `COORD_OVERLAP` warning
(or `STALE_BASE_OBSERVED` when the bases differ) in `warnings`/`overlaps`, never as a
refusal to write. The formula is **tool = always-write + warn, agent =
stop-on-real-overlap**: on a real overlap with another active owner on the same region
the deciding agent stops and coordinates, but coordctl itself does not block.

## Commit Scope: report vs check

Both commands are read-only and allow file-level subset commits: a commit may include
selected complete files while other files remain uncommitted and visible in `git status`.

`coordctl commit-scope-report` never fails (`ok:true` always). It returns the
staged/unstaged/untracked/unmerged/partial breakdown plus warnings/observations
(`NO_STAGED_CHANGES`, `UNCOMMITTED_OWNER_STATE_VISIBLE`, …) so the owner/agent can decide.

`coordctl commit-scope-check` is a gate that hard-fails (`ok:false`) ONLY for genuinely
dangerous states:

- unmerged paths (`UNMERGED_STATE`)
- a staged file that also has unstaged changes (`PARTIAL_FILE_STAGED`)

"No staged changes" is a warning, not a failure. For `PARTIAL_FILE_STAGED` an agent may
stage the complete file itself when doing so pulls in no foreign changes; only foreign or
unclear residue requires stopping and asking the owner. Agents MUST NOT stash, clean,
restore, or create a separate clean worktree/repo to hide another owner's local state.

## Cleanup Discipline

Agent sessions must finish in one of these final states:

- `merged`
- `released`
- `abandoned`
- `blocked-owner`
- `failed-cleanup`

`coordctl cleanup` is dry-run by default unless `--apply` is passed. Applying cleanup releases
active leases, marks the session final, and can optionally remove the recorded worktree and local
branch. Branch deletion uses `git branch -d`, so unmerged branches are not deleted silently.
Worktree deletion uses `git worktree remove` without force, so dirty worktrees stop cleanup and
the session becomes `failed-cleanup`.

`coordctl gc` is also dry-run by default. It deletes expired/final session rows and released/expired
leases only with `--apply`; the transactional `coord_events` audit table is preserved (permanent audit).
`gc --dry-run` also reports `runtime_sizes`. `gc --rotate-events --apply` archives the append-only
`events.jsonl` mirror into the state-dir `archive/` folder without touching `coord_events`.
