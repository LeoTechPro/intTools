#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="${COORDCTL_INSTALL_BIN:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/coordctl" "$BIN_DIR/coordctl"

echo "coordctl install: linked coordctl launcher into $BIN_DIR"
echo "coordctl MCP is exposed by: $TOOLS_ROOT/codex/bin/mcp-intdata-cli.sh --profile coordctl (or intdata-control)"
