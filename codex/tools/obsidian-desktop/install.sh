#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

mkdir -p /home/leon/.local/bin /home/leon/.local/share/applications /home/leon/.config/obsidian

ln -sfn "$ROOT_DIR/launcher.sh" /home/leon/.local/bin/obsidian
ln -sfn "$ROOT_DIR/obsidian-memory.desktop" /home/leon/.local/share/applications/obsidian-memory.desktop
ln -sfn "$ROOT_DIR/obsidian.json" /home/leon/.config/obsidian/obsidian.json

update-desktop-database /home/leon/.local/share/applications >/dev/null 2>&1 || true

echo "Installed symlinks:" 
readlink -f /home/leon/.local/bin/obsidian
readlink -f /home/leon/.local/share/applications/obsidian-memory.desktop
readlink -f /home/leon/.config/obsidian/obsidian.json
