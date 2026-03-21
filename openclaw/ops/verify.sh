#!/usr/bin/env bash
set -euo pipefail

DEFAULT_NODE_DIR="$HOME/.nvm/versions/node/v24.8.0/bin"

if [[ -d "$DEFAULT_NODE_DIR" ]]; then
  export PATH="$DEFAULT_NODE_DIR:$PATH"
fi

command -v openclaw >/dev/null 2>&1

for _ in $(seq 1 30); do
  if systemctl --user is-active --quiet openclaw-gateway.service; then
    break
  fi
  sleep 1
done

systemctl --user is-active --quiet openclaw-gateway.service

TMP_STATUS="$(mktemp)"
trap 'rm -f "$TMP_STATUS"' EXIT

openclaw gateway status --json --no-probe >"$TMP_STATUS"

if ! command -v jq >/dev/null 2>&1; then
  echo "openclaw verify: jq is required for config-path checks" >&2
  exit 1
fi

systemctl --user cat openclaw-gateway.service | rg -n 'OPENCLAW_GATEWAY_TOKEN=|/git/[^[:space:]]*openclaw|WorkingDirectory=/git/' -S && {
  echo "openclaw verify: service still references in-tree runtime paths or embedded token" >&2
  exit 1
} || true

rg -n '"/git/[^"]*openclaw|"/git/[^"]*workspace' "$TMP_STATUS" -S && {
  echo "openclaw verify: gateway status still reports in-tree runtime paths" >&2
  exit 1
} || true

jq -e --arg openclawConfig "$HOME/.openclaw/openclaw.json" '.config.cli.path == $openclawConfig and .config.daemon.path == $openclawConfig' "$TMP_STATUS" >/dev/null || {
  echo "openclaw verify: gateway status does not point to canonical ~/.openclaw/openclaw.json" >&2
  exit 1
}

echo "openclaw verify: ok"
