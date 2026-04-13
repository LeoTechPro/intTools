#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

API_BASE_URL="${API_BASE_URL:-https://api-dev.punkt-b.pro}"
SERVICE_ROLE_KEY="${SERVICE_ROLE_KEY:-}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-20}"
API_HOST_HEADER="${API_HOST_HEADER:-}"

if [[ -z "${SERVICE_ROLE_KEY}" ]]; then
  echo "SMOKE_FAIL: SERVICE_ROLE_KEY is required"
  exit 1
fi

curl_base=(
  curl -sS --fail-with-body --max-time "${REQUEST_TIMEOUT}"
)

if [[ -n "${API_HOST_HEADER}" ]]; then
  curl_base+=(-H "Host: ${API_HOST_HEADER}")
fi

auth_headers=(
  -H "apikey: ${SERVICE_ROLE_KEY}"
  -H "Authorization: Bearer ${SERVICE_ROLE_KEY}"
)

check_http_code() {
  local name="$1"
  local method="$2"
  local url="$3"
  local expected="$4"
  local body="${5:-}"

  local response
  local http_code
  if [[ -n "${body}" ]]; then
    response="$("${curl_base[@]}" -w $'\n%{http_code}' -X "${method}" "${url}" "${auth_headers[@]}" -H 'Content-Type: application/json' -d "${body}" || true)"
  else
    response="$("${curl_base[@]}" -w $'\n%{http_code}' -X "${method}" "${url}" "${auth_headers[@]}" || true)"
  fi
  http_code="${response##*$'\n'}"
  local response_body="${response%$'\n'*}"

  if [[ "${http_code}" != "${expected}" ]]; then
    echo "SMOKE_FAIL: ${name} expected ${expected}, got ${http_code}"
    printf '%s\n' "${response_body}"
    exit 1
  fi

  echo "SMOKE_OK: ${name} (${http_code})"
}

check_http_code \
  "rest.user_profiles.health" \
  "GET" \
  "${API_BASE_URL}/rest/v1/user_profiles?select=id&limit=1" \
  "200"

check_http_code \
  "functions.main.health" \
  "POST" \
  "${API_BASE_URL}/functions/v1/main" \
  "200" \
  "{}"

check_http_code \
  "functions.create-user.validation" \
  "POST" \
  "${API_BASE_URL}/functions/v1/create-user" \
  "401" \
  "{}"

echo "SMOKE_OK: api/edge baseline passed"
