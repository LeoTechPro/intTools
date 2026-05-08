# coordctl

`coordctl` is a parallel, Git-aware coordination utility for multi-agent edits.

It replaces active `lockctl` usage for current Codex project coordination. `lockctl`
remains in the repo as a legacy CLI for manual diagnostics with direct owner approval.

## Runtime State

Runtime state is stored outside source control:

- default: `D:\int\tools\.runtime\coordctl` or `/int/tools/.runtime/coordctl`
- override: `COORDCTL_STATE_DIR`

Runtime files:

- `coord.sqlite`
- `events.jsonl`

## CLI

```bash
coordctl session-start --repo-root /int/tools --owner codex:session --branch agent/INT-1/a --base main --format json
coordctl intent-acquire --repo-root /int/tools --path README.md --owner codex:session --base main --region-kind hunk --region-id 12:18 --lease-sec 3600 --format json
coordctl status --repo-root /int/tools --format json
coordctl commit-scope-check --repo-root /int/tools --format json
coordctl heartbeat --session-id <session-id> --format json
coordctl merge-dry-run --repo-root /int/tools --target main --branch agent/INT-1/a --format json
coordctl release --session-id <session-id> --format json
coordctl cleanup --session-id <session-id> --final-state released --dry-run --format json
coordctl cleanup --session-id <session-id> --final-state merged --delete-worktree --delete-branch --apply --format json
coordctl gc --dry-run --format json
```

## Region Model v1

- `file`: coarse fallback for files that cannot be safely split.
- `hunk`: MVP coordination unit, identified by a base-file line range such as `12:18`.
- `symbol`, `json_path`, and `section`: reserved for future semantic extractors and rejected in v1.

Conflict detection is advisory and optimistic: overlapping active leases from another
owner are rejected before write/merge, while non-overlapping hunks in the same file are allowed.

## Commit Scope Check

`coordctl commit-scope-check` is a read-only pre-commit guard for owner-state transparency.
It allows file-level subset commits: a commit may include selected complete files while other
files remain uncommitted and visible in `git status`.

It fails when a commit would publish an incomplete file-level state:

- unmerged paths
- a staged file that also has unstaged changes
- no staged changes

Agents must stop and ask the owner instead of staging hunks selectively, stashing, cleaning,
restoring, or creating a separate clean worktree/repo to hide local state from publication.

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
leases only with `--apply`; the audit trail remains in `coord_events` and `events.jsonl`.
