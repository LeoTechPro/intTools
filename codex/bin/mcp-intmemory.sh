#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
# shellcheck source=../lib/codex-env.sh
source "$ROOT_DIR/lib/codex-env.sh"

env_name="intbrain-agent.env"
codex_source_env_file "$env_name" || true

if [[ -z "${INTMEMORY_OWNER_ID:-}" ]]; then
  cat >&2 <<EOF
INTMEMORY_OWNER_ID is not set.
Export it before starting Codex/OpenClaw or place it in $(codex_primary_env_hint "$env_name").
EOF
  exit 1
fi

exec python3 "$ROOT_DIR/bin/mcp-intmemory.py"
