#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
# shellcheck source=../lib/codex-env.sh
source "$ROOT_DIR/lib/codex-env.sh"

env_name="intbrain-agent.env"
codex_source_env_file "$env_name" || true

if [[ -z "${INTBRAIN_AGENT_ID:-}" || -z "${INTBRAIN_AGENT_KEY:-}" ]]; then
  cat >&2 <<EOF
INTBRAIN_AGENT_ID/INTBRAIN_AGENT_KEY are not set.
Set them in $(codex_primary_env_hint "$env_name") or export them before starting Codex/OpenClaw.
Legacy fallback: $(codex_legacy_env_hint "$env_name")
EOF
  exit 1
fi

exec python3 "$ROOT_DIR/bin/mcp-intbrain.py"

