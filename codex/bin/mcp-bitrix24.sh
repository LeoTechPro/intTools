#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
# shellcheck source=../lib/codex-env.sh
source "$ROOT_DIR/lib/codex-env.sh"

env_name="bitrix24-mcp.env"
APP_BIN="${HOME}/.local/bin/bitrix24-mcp"
codex_source_env_file "$env_name" || true

if [[ -z "${BITRIX_WEBHOOK_URL:-}" ]]; then
  cat >&2 <<EOF
mcp-bitrix24: BITRIX_WEBHOOK_URL is not set.
Set it in $(codex_primary_env_hint "$env_name") or export it before starting Codex.
Legacy fallback: $(codex_legacy_env_hint "$env_name")
EOF
  exit 1
fi

exec "${APP_BIN}"
