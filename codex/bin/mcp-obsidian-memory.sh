#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
SERVER_DIR="$ROOT_DIR/tools/mcp-obsidian-memory"

resolve_node_bin() {
  local candidate
  local default_nvm_node="$HOME/.nvm/versions/node/v24.8.0/bin/node"

  for candidate in \
    "${OBSIDIAN_MEMORY_NODE_BIN:-}" \
    "${NVM_BIN:-}/node" \
    "$default_nvm_node" \
    "$(command -v node 2>/dev/null || true)"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

NODE_BIN="$(resolve_node_bin)" || {
  echo "mcp-obsidian-memory: node binary not found. Set OBSIDIAN_MEMORY_NODE_BIN or install node." >&2
  exit 1
}

exec "$NODE_BIN" "$SERVER_DIR/src/index.mjs"
