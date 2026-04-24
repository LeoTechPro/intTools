#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/venv"
REQUIREMENTS="$ROOT/requirements.txt"
SERVICE="intdata-web"

log() {
  printf '[rebuild_service] %s\n' "$1"
}

log "Stopping $SERVICE" || true
if sudo -n systemctl is-active --quiet "$SERVICE"; then
  sudo -n systemctl stop "$SERVICE"
fi

log "Removing existing virtual environment"
rm -rf "$VENV"

log "Creating virtual environment"
python3 -m venv "$VENV"
source "$VENV/bin/activate"

log "Upgrading pip"
pip install --upgrade pip >/tmp/rebuild_service_pip.log

log "Installing requirements"
pip install -r "$REQUIREMENTS" >/tmp/rebuild_service_deps.log

deactivate

if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  log "uvicorn executable not found after install" >&2
  exit 1
fi

log "Restarting $SERVICE"
sudo -n systemctl restart "$SERVICE"

log "Tail service logs"
sudo -n journalctl -u "$SERVICE" -n 50 --no-pager
