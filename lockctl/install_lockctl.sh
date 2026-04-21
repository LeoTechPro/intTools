#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="${LOCKCTL_INSTALL_BIN:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/lockctl" "$BIN_DIR/lockctl"
ln -sf "$SCRIPT_DIR/lockctl" "$BIN_DIR/lockctl.cmd"

echo "lockctl install: linked lockctl launcher into $BIN_DIR"
echo "lockctl MCP is exposed by: $TOOLS_ROOT/codex/bin/mcp-intdata-cli.sh --profile intdata-control"
