#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
# shellcheck source=../lib/codex-env.sh
source "$ROOT_DIR/lib/codex-env.sh"

env_name="intbrain-agent.env"
codex_source_env_file "$env_name" || true

exec python3 "$ROOT_DIR/bin/intmemory.py" "$@"
