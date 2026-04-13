#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="${SCRIPT_DIR}/../../scripts/codex/int_git_sync_gate.py"

if [[ ! -f "${ENGINE}" ]]; then
  echo "int_git_sync_gate.py not found: ${ENGINE}" >&2
  exit 2
fi

exec python3 "${ENGINE}" "$@"
