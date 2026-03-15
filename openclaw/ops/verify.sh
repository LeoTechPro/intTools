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

systemctl --user cat openclaw-gateway.service | rg -n '/git/openclaw/bin/openclaw|/git/openclaw/node_modules|OPENCLAW_GATEWAY_TOKEN=' -S && {
  echo "openclaw verify: service still references legacy /git/openclaw runtime or embedded token" >&2
  exit 1
} || true

rg -n '"/git/openclaw/bin/openclaw"|"/git/openclaw/openclaw.json"|"/git/openclaw/state"' "$TMP_STATUS" -S && {
  echo "openclaw verify: gateway status still reports legacy /git/openclaw paths" >&2
  exit 1
} || true

echo "openclaw verify: ok"
