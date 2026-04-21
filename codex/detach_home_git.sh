#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_ROOT="${ASSETS_ROOT:-/int/tools/codex/assets/codex-home}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

if (( DRY_RUN == 1 )); then
  if [[ -d "$CODEX_HOME/.git" ]]; then
    echo "dry-run: Codex home git detach is retired; git directory exists at $CODEX_HOME/.git"
  else
    echo "dry-run: Codex home git detach is retired; no git directory found at $CODEX_HOME/.git"
  fi
  exit 0
fi

echo "Codex home git detach is retired; use native Codex state management or explicit manual owner action." >&2
exit 1
