#!/usr/bin/env bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CODEX_RUNTIME_ROOT="${CODEX_RUNTIME_ROOT:-/int/.runtime}"
CODEX_SECRETS_ROOT="${CODEX_SECRETS_ROOT:-$CODEX_RUNTIME_ROOT/codex-secrets}"
LEGACY_CODEX_VAR_ROOT="${LEGACY_CODEX_VAR_ROOT:-$CODEX_HOME/var}"

codex_primary_env_hint() {
  local name="$1"
  printf '%s/%s\n' "$CODEX_SECRETS_ROOT" "$name"
}

codex_legacy_env_hint() {
  local name="$1"
  printf '%s/%s\n' "$LEGACY_CODEX_VAR_ROOT" "$name"
}

codex_locate_env_file() {
  local name="$1"
  local primary legacy
  primary="$(codex_primary_env_hint "$name")"
  legacy="$(codex_legacy_env_hint "$name")"
  if [[ -f "$primary" ]]; then
    printf '%s\n' "$primary"
    return 0
  fi
  if [[ -f "$legacy" ]]; then
    printf '%s\n' "$legacy"
    return 0
  fi
  return 1
}

codex_source_env_file() {
  local name="$1"
  local env_file
  if ! env_file="$(codex_locate_env_file "$name")"; then
    return 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}
