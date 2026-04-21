#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
# shellcheck source=../lib/codex-env.sh
source "$ROOT_DIR/lib/codex-env.sh"

env_name="timeweb-cloud.env"
codex_source_env_file "$env_name" || true

if [[ -z "${TIMEWEB_TOKEN:-}" ]]; then
  cat >&2 <<EOF
TIMEWEB_TOKEN is not set.
Set it in $(codex_primary_env_hint "$env_name") before using twc.
EOF
  exit 1
fi

export TWC_TOKEN="$TIMEWEB_TOKEN"
exec twc "$@"
