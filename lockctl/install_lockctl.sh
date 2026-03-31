#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="${LOCKCTL_INSTALL_BIN:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/lockctl" "$BIN_DIR/lockctl"
ln -sf "$TOOLS_ROOT/codex/bin/mcp-lockctl.sh" "$BIN_DIR/lockctl-mcp"

echo "lockctl install: linked launchers into $BIN_DIR"
