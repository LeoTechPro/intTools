#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
DEFAULT_NODE_DIR="$HOME/.nvm/versions/node/v24.8.0/bin"

if [[ -d "$DEFAULT_NODE_DIR" ]]; then
  export PATH="$DEFAULT_NODE_DIR:$PATH"
fi

command -v openclaw >/dev/null 2>&1 || {
  echo "openclaw not found in PATH. Install it first, for example:" >&2
  echo "  npm install -g openclaw@latest" >&2
  exit 1
}

mkdir -p "$HOME/.config/systemd/user/openclaw-gateway.service.d"

install -m 0644 \
  "$ROOT_DIR/systemd/openclaw-gateway.service.d/gog-runtime.conf" \
  "$HOME/.config/systemd/user/openclaw-gateway.service.d/gog-runtime.conf"

install -m 0644 \
  "$ROOT_DIR/systemd/openclaw-gateway.service.d/limits.conf" \
  "$HOME/.config/systemd/user/openclaw-gateway.service.d/limits.conf"

openclaw gateway install --force --runtime node --port "$PORT"
systemctl --user daemon-reload

echo "openclaw install: official daemon installed with overlay drop-ins"
systemctl --user status openclaw-gateway.service --no-pager -n 20
