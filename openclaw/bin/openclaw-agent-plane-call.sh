#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  openclaw-agent-plane-call.sh --tool <name> [--args-json JSON] [--principal-json JSON] [--approval-ref REF]
EOF
  exit 64
}

TOOL=""
ARGS_JSON="{}"
PRINCIPAL_JSON='{"id":"openclaw","chat_id":"unknown"}'
APPROVAL_REF=""
URL="${AGENT_PLANE_URL:-http://127.0.0.1:9192}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) TOOL="${2:-}"; shift 2 ;;
    --args-json) ARGS_JSON="${2:-}"; shift 2 ;;
    --principal-json) PRINCIPAL_JSON="${2:-}"; shift 2 ;;
    --approval-ref) APPROVAL_REF="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "$TOOL" ]] || usage

python3 - "$URL" "$TOOL" "$ARGS_JSON" "$PRINCIPAL_JSON" "$APPROVAL_REF" <<'PY'
import json
import sys
import urllib.error
import urllib.request

url, tool, args_json, principal_json, approval_ref = sys.argv[1:6]
payload = {
    "facade": "openclaw",
    "principal": json.loads(principal_json),
    "tool": tool,
    "args": json.loads(args_json),
}
if approval_ref:
    payload["approval_ref"] = approval_ref
request = urllib.request.Request(
    url.rstrip("/") + "/v1/tools/call",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    method="POST",
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(request, timeout=60) as response:
        print(response.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    print(exc.read().decode("utf-8"))
    raise SystemExit(1)
PY
