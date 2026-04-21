#!/usr/bin/env bash
set -euo pipefail

ASSETS_ROOT="${ASSETS_ROOT:-/int/tools/codex/assets/codex-home}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PROJECTS_ROOT="${PROJECTS_ROOT:-/int/tools/codex/projects}"

if [[ "${1:-}" == "--dry-run" ]]; then
  cat <<EOF
dry-run: Codex home sync is retired; use native Codex plugin/skill/config mechanisms.
legacy source: $ASSETS_ROOT
legacy projects source: $PROJECTS_ROOT
legacy destination: $CODEX_HOME
EOF
  exit 0
fi

echo "Codex home sync is retired; use native Codex plugin/skill/config mechanisms." >&2
exit 1
