#!/usr/bin/env bash
set -euo pipefail

ASSETS_ROOT="${ASSETS_ROOT:-/git/tools/codex/assets/codex-home}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PROJECTS_ROOT="${PROJECTS_ROOT:-/git/tools/codex/projects}"
RSYNC_OPTS=(-a --no-group --exclude '__pycache__/' --exclude '*.pyc')

if [[ "${1:-}" == "--dry-run" ]]; then
  RSYNC_OPTS+=(--dry-run --itemize-changes)
fi

if [[ ! -f "$ASSETS_ROOT/AGENTS.md" ]]; then
  echo "missing managed assets root: $ASSETS_ROOT" >&2
  exit 1
fi

mkdir -p "$CODEX_HOME"

sync_file() {
  local src="$1"
  local dst="$2"
  rsync "${RSYNC_OPTS[@]}" "$src" "$dst"
}

sync_dir_delete() {
  local src="$1"
  local dst="$2"
  mkdir -p "$dst"
  rsync "${RSYNC_OPTS[@]}" --delete "$src" "$dst"
}

sync_dir_overlay() {
  local src="$1"
  local dst="$2"
  shift 2
  mkdir -p "$dst"
  rsync "${RSYNC_OPTS[@]}" "$@" "$src" "$dst"
}

sync_file "$ASSETS_ROOT/AGENTS.md" "$CODEX_HOME/"
sync_file "$ASSETS_ROOT/.personality_migration" "$CODEX_HOME/"
sync_file "$ASSETS_ROOT/version.json" "$CODEX_HOME/"

sync_dir_delete "$ASSETS_ROOT/rules/" "$CODEX_HOME/rules/"
sync_dir_delete "$ASSETS_ROOT/prompts/" "$CODEX_HOME/prompts/"
sync_dir_delete "$ASSETS_ROOT/skills/" "$CODEX_HOME/skills/"

if [[ -d "$PROJECTS_ROOT" ]]; then
  sync_dir_delete "$PROJECTS_ROOT/" "$CODEX_HOME/projects/"
fi

echo "synced runtime-facing config assets from $ASSETS_ROOT into $CODEX_HOME"
