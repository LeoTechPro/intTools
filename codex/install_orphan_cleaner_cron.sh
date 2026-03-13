#!/usr/bin/env bash
set -euo pipefail

CANONICAL_CMD="*/5 * * * * /git/scripts/codex/cleanup_agent_orphans.sh >/dev/null 2>&1 # probe-agent-orphan-cleaner"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

(crontab -l 2>/dev/null || true) > "$TMP_FILE"

# Remove legacy and duplicate cleaner entries, keep unrelated crons untouched.
sed -i '/probe-agent-orphan-cleaner/d;/codex-agent-orphan-cleaner/d;/cleanup-agent-orphans\.sh/d;/cleanup_agent_orphans\.sh/d' "$TMP_FILE"

printf '%s\n' "$CANONICAL_CMD" >> "$TMP_FILE"
crontab "$TMP_FILE"

echo "installed canonical cleaner cron entry:"
crontab -l | rg 'probe-agent-orphan-cleaner|cleanup-agent-orphans\.sh|cleanup_agent_orphans\.sh' || true
