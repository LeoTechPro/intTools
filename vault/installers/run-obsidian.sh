#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/.tools/obsidian/Obsidian.AppImage" "$SCRIPT_DIR"
