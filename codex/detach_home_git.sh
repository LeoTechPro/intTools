#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_ROOT="${ASSETS_ROOT:-/git/tools/codex/assets/codex-home}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

if [[ ! -f "$ASSETS_ROOT/AGENTS.md" ]]; then
  echo "missing managed assets root: $ASSETS_ROOT" >&2
  exit 1
fi

"$SCRIPT_DIR/sync_runtime_from_repo.sh" "${1:-}"

for forbidden in \
  auth.json \
  config.toml \
  history.jsonl \
  internal_storage.json \
  session_index.jsonl \
  var \
  tools \
  tools/openclaw/openclaw.json \
  tools/openclaw/secrets/telegram.token; do
  if [[ -e "$ASSETS_ROOT/$forbidden" ]]; then
    echo "forbidden runtime payload in managed assets: $forbidden" >&2
    exit 1
  fi
done

if (( DRY_RUN == 1 )); then
  echo "dry-run: ~/.codex git would be detached"
  exit 0
fi

if [[ ! -d "$CODEX_HOME/.git" ]]; then
  echo "~/.codex git is already detached"
  exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$CODEX_HOME/.git.detached-$STAMP"

mv "$CODEX_HOME/.git" "$BACKUP_DIR"
cat >"$CODEX_HOME/.git-detached" <<EOF
detached_at_utc=$STAMP
assets_root=$ASSETS_ROOT
git_backup=$BACKUP_DIR
note=edit managed assets in /git/tools/codex/assets/codex-home and refresh runtime via /git/tools/codex/sync_runtime_from_repo.sh
EOF

echo "detached ~/.codex git into $BACKUP_DIR"
