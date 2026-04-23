#!/bin/sh
set -eu

CONFIG_PATH="${V2RAYA_CONFIG_PATH:-/var/snap/v2raya/current/etc/config.json}"

if [ ! -f "$CONFIG_PATH" ]; then
  exit 0
fi

tmp="${CONFIG_PATH}.codex-no-quic.$$"

/usr/bin/python3 - "$CONFIG_PATH" "$tmp" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

data = json.loads(src.read_text(encoding="utf-8"))

def strip_quic(value):
    if isinstance(value, dict):
        return {k: strip_quic(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_quic(v) for v in value if v != "quic"]
    return value

dst.write_text(
    json.dumps(strip_quic(data), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

if ! cmp -s "$CONFIG_PATH" "$tmp"; then
  cat "$tmp" > "$CONFIG_PATH"
fi

rm -f "$tmp"
