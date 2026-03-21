#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

failures=0

smoke_check() {
  local label="$1"
  local url="$2"
  local opts="${3:--fsS}"
  local mode="${4:-strict}"
  set +e
  curl ${opts} --max-time 10 -o /dev/null "$url"
  local status=$?
  set -e
  if [[ $status -eq 0 ]]; then
    echo "[OK] $label $url"
  else
    if [[ "$mode" == optional ]]; then
      echo "[SKIP] $label $url (curl exit $status)" >&2
    else
      echo "[FAIL] $label $url (curl exit $status)" >&2
      failures=1
    fi
  fi
}

smoke_check "nexus-health" "http://localhost:8080/health" "-fsSk"
smoke_check "nexus-ping" "http://localhost:8080/api/nexus/v1/ping" "-fsSk"
smoke_check "nexus-modules" "http://localhost:8080/api/nexus/v1/modules" "-fsSk"
smoke_check "matrix-versions" "https://chat.dev.intdata.pro/_matrix/client/versions" "-fsS" optional

# IAM stack checks
smoke_check "keycloak-openid" "http://127.0.0.1:${ID_KEYCLOAK_HTTP_PORT_LEGACY:-8080}/realms/${ID_KEYCLOAK_REALM:-intdata}/.well-known/openid-configuration" "-fsSk"
KILLBILL_SCHEME="${ID_KILLBILL_SCHEME:-http}"
KILLBILL_PORT="${ID_KILLBILL_HTTP_PORT:-8081}"
KILLBILL_BASE_URL="${KILLBILL_SCHEME}://127.0.0.1:${KILLBILL_PORT}"
KILLBILL_CURL_OPTS="-fsS"
if [[ "$KILLBILL_SCHEME" == https ]]; then
  KILLBILL_CURL_OPTS="-fsSk"
fi
smoke_check "killbill-health" "${KILLBILL_BASE_URL}/1.0/healthcheck" "$KILLBILL_CURL_OPTS"

# OpenBao (Vault) health check — требуется валидный токен
OPENBAO_ADDR_VALUE="${ID_OPENBAO_ADDR:-${OPENBAO_ADDR:-}}"
OPENBAO_TOKEN_VALUE="${ID_OPENBAO_TOKEN:-${OPENBAO_ROOT_TOKEN:-}}"
OPENBAO_HTTP_PORT_VALUE="${OPENBAO_HTTP_PORT:-8200}"
if [[ -n "$OPENBAO_ADDR_VALUE" ]]; then
  OPENBAO_HEALTH_URL="${OPENBAO_ADDR_VALUE%/}/v1/sys/health?standbyok=true&perfstandbyok=true"
  if [[ -n "$OPENBAO_TOKEN_VALUE" ]]; then
    set +e
    curl -fsSk "$OPENBAO_HEALTH_URL" -H "X-Vault-Token: ${OPENBAO_TOKEN_VALUE}" -o /dev/null
    status=$?
    set -e
    if [[ $status -eq 0 ]]; then
      echo "[OK] openbao $OPENBAO_HEALTH_URL"
    else
      FALLBACK_URL="http://127.0.0.1:${OPENBAO_HTTP_PORT_VALUE}/v1/sys/health?standbyok=true&perfstandbyok=true"
      set +e
      curl -fsS "$FALLBACK_URL" -H "X-Vault-Token: ${OPENBAO_TOKEN_VALUE}" -o /dev/null
      fallback_status=$?
      set -e
      if [[ $fallback_status -eq 0 ]]; then
        echo "[WARN] openbao fallback $FALLBACK_URL"
      else
        echo "[FAIL] openbao $OPENBAO_HEALTH_URL (curl exit $status, fallback exit $fallback_status)" >&2
        failures=1
      fi
    fi
  else
    echo "openbao health skipped (no token)" >&2
  fi
fi

if [[ $failures -ne 0 ]]; then
  exit 1
fi
