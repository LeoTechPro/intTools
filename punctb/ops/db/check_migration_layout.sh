#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-backend/init/migrations}"
TOP_LEVEL_MAX_LINES="${TOP_LEVEL_MAX_LINES:-250}"
FRAGMENT_MAX_LINES="${FRAGMENT_MAX_LINES:-400}"
STRICT_TOP_LEVEL_MAX="${STRICT_TOP_LEVEL_MAX:-0}"

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
  echo "SMOKE_FAIL: migrations dir not found: $MIGRATIONS_DIR"
  exit 1
fi

failed=0

fail() {
  failed=1
  echo "SMOKE_FAIL: $1"
}

resolve_include_target() {
  local wrapper_path="$1"
  local include_path="$2"
  local wrapper_dir
  wrapper_dir="$(dirname "$wrapper_path")"
  readlink -f "$wrapper_dir/$include_path"
}

while IFS= read -r wrapper_path; do
  [[ -n "$wrapper_path" ]] || continue

  mapfile -t include_lines < <(grep -E '^\\ir[[:space:]]+' "$wrapper_path" || true)
  if (( ${#include_lines[@]} == 0 )) && [[ "$STRICT_TOP_LEVEL_MAX" != "1" ]]; then
    continue
  fi

  wrapper_lines="$(wc -l < "$wrapper_path" | tr -d '[:space:]')"
  if (( wrapper_lines > TOP_LEVEL_MAX_LINES )); then
    fail "top-level migration exceeds ${TOP_LEVEL_MAX_LINES} lines: ${wrapper_path#$MIGRATIONS_DIR/} (${wrapper_lines})"
  fi

  for include_line in "${include_lines[@]}"; do
    [[ -n "$include_line" ]] || continue

    include_path="$(printf '%s\n' "$include_line" | sed -E "s/^\\\\ir[[:space:]]+['\"]?([^'\"]+)['\"]?$/\\1/")"
    resolved_path="$(resolve_include_target "$wrapper_path" "$include_path")"
    migrations_root="$(readlink -f "$MIGRATIONS_DIR")"

    if [[ "$resolved_path" != "$migrations_root/"* ]]; then
      fail "include escapes migrations dir: ${wrapper_path#$MIGRATIONS_DIR/} -> $include_path"
      continue
    fi

    if [[ ! -f "$resolved_path" ]]; then
      fail "include target missing: ${wrapper_path#$MIGRATIONS_DIR/} -> $include_path"
      continue
    fi

    fragment_lines="$(wc -l < "$resolved_path" | tr -d '[:space:]')"
    if (( fragment_lines > FRAGMENT_MAX_LINES )); then
      fail "fragment exceeds ${FRAGMENT_MAX_LINES} lines: ${resolved_path#$MIGRATIONS_DIR/} (${fragment_lines})"
    fi
  done
done < <(find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name '*.sql' | sort)

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi

echo "SMOKE_OK: migration layout passed (wrapper size/includes/fragments)"
