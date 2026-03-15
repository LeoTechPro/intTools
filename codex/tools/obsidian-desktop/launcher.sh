#!/usr/bin/env bash
set -euo pipefail

APPDIR="${OBSIDIAN_APPDIR:-/home/leon/.local/opt/obsidian/current}"
APPIMAGE="${OBSIDIAN_APPIMAGE:-/home/leon/.local/opt/obsidian/Obsidian.AppImage}"
VAULT="${OBSIDIAN_VAULT:-/2brain}"

export APPDIR
export APPIMAGE

exec "$APPDIR/AppRun" --no-sandbox "$VAULT" "$@"
