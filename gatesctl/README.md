# gatesctl

`gatesctl` — machine-wide runtime для gate receipts, approvals и commit binding поверх issue-bound процесса.

## Shell UX

Используйте публичную точку входа:

```bash
gatesctl
gatesctl --help
gatesctl help verify
```

## Runtime model

- Runtime truth хранится в SQLite, не в проектных YAML/JSON ledgers.
- GitHub Issue остаётся источником human context/evidence, но normalized state хранится в `gatesctl`.
- `lockctl` отвечает только за file lease и не хранит review/gate историю.
- Bound receipts не удаляются `gc`; очищается только sync-cache и старые unbound записи.

Runtime files:

- `GATESCTL_STATE_DIR=/home/leon/.codex/memories/gatesctl`
- SQLite: `/home/leon/.codex/memories/gatesctl/gates.sqlite`
- Event log: `/home/leon/.codex/memories/gatesctl/events.jsonl`

## Common examples

```bash
gatesctl plan-scope \
  --repo-root /int/punctb \
  --issue 1224 \
  --files .agents/scripts/issue_commit.sh

gatesctl approve \
  --repo-root /int/punctb \
  --issue 1224 \
  --gate docs-sync \
  --decision approve \
  --actor gatesctl \
  --role system \
  --files .agents/scripts/issue_commit.sh

gatesctl verify \
  --repo-root /int/punctb \
  --issue 1224 \
  --stage commit \
  --files .agents/scripts/issue_commit.sh \
  --sync-issue

gatesctl bind-commit \
  --repo-root /int/punctb \
  --commit-sha HEAD

gatesctl audit-range \
  --repo-root /int/punctb \
  --target-branch dev \
  --range '@{upstream}..HEAD'
```

## Notes

- Не редактируйте SQLite и `events.jsonl` напрямую.
- Repo-specific правила задаются policy-файлом, обычно `.agents/policy/gates.v1.yaml`.
- Для self-hosted remote можно использовать sample hook: `hooks/pre-receive.sample`.

## Server-side hook

Sample `pre-receive` hook ожидает:

- bare/self-hosted remote, где доступен `gatesctl`;
- `GATESCTL_REPO_ROOT` — рабочий клон/checkout репозитория с policy-файлом;
- `GATESCTL_TARGET_BRANCH` при необходимости фиксированной ветки.

На GitHub.com такой hook не устанавливается; там этот sample служит только шаблоном для собственного central remote.
