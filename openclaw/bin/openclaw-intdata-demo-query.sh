#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  openclaw-intdata-demo-query.sh assert
  openclaw-intdata-demo-query.sh list [app_code] [--passwords]
  openclaw-intdata-demo-query.sh perms <app_code> <role_code>
EOF
  exit 64
}

[[ $# -ge 1 ]] || usage

COMMAND="$1"
shift || true

ENV_FILE="${INTDATA_ENV_FILE:-/int/data/.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

SUPABASE_URL="${INTDATA_SUPABASE_URL:-${SUPABASE_URL:-https://api.intdata.pro}}"
SERVICE_KEY="${INTDATA_SERVICE_ROLE_KEY:-${SUPABASE_SERVICE_ROLE_KEY:-${SERVICE_ROLE_KEY:-}}}"

if [[ -z "$SERVICE_KEY" ]]; then
  echo "openclaw-intdata-demo-query: missing service role key; set INTDATA_SERVICE_ROLE_KEY or provide /int/data/.env" >&2
  exit 78
fi

rpc() {
  local fn="$1"
  local payload="${2:-{}}"

  curl -fsS \
    -X POST \
    "${SUPABASE_URL%/}/rest/v1/rpc/${fn}" \
    -H "apikey: ${SERVICE_KEY}" \
    -H "Authorization: Bearer ${SERVICE_KEY}" \
    -H "Accept-Profile: app" \
    -H "Content-Profile: app" \
    -H "Content-Type: application/json" \
    --data "${payload}"
}

pretty_print() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  else
    cat
  fi
}

case "$COMMAND" in
  assert)
    rpc "demo_accounts_assert_coverage_v1" '{}' | pretty_print
    ;;
  list)
    APP_CODE=""
    INCLUDE_PASSWORDS="false"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --passwords)
          INCLUDE_PASSWORDS="true"
          shift
          ;;
        *)
          if [[ -n "$APP_CODE" ]]; then
            usage
          fi
          APP_CODE="$1"
          shift
          ;;
      esac
    done
    if [[ -n "$APP_CODE" ]]; then
      rpc "demo_accounts_list_v1" "$(printf '{"p_app_code":"%s","p_include_password":%s}' "$APP_CODE" "$INCLUDE_PASSWORDS")" | pretty_print
    else
      rpc "demo_accounts_list_v1" "$(printf '{"p_app_code":null,"p_include_password":%s}' "$INCLUDE_PASSWORDS")" | pretty_print
    fi
    ;;
  perms)
    [[ $# -eq 2 ]] || usage
    rpc "demo_account_perms_v1" "$(printf '{"p_app_code":"%s","p_role_code":"%s"}' "$1" "$2")" | pretty_print
    ;;
  *)
    usage
    ;;
esac
