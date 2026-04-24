#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ROISTAT_BASE_URL:-http://127.0.0.1:8080}"
TOKEN="${ROISTAT_TOKEN:-}"

check_response() {
    local url="$1"
    local expected_code="$2"
    local expected_body="$3"
    local body_file
    body_file="$(mktemp)"

    local code
    code="$(curl -sS -o "$body_file" -w '%{http_code}' "$url")"
    if [[ "$code" != "$expected_code" ]]; then
        echo "Unexpected HTTP code for $url: $code" >&2
        cat "$body_file" >&2
        rm -f "$body_file"
        exit 1
    fi

    if ! grep -q "$expected_body" "$body_file"; then
        echo "Unexpected body for $url" >&2
        cat "$body_file" >&2
        rm -f "$body_file"
        exit 1
    fi

    rm -f "$body_file"
}

check_response "${BASE_URL%/}/roistat/crm.php" 400 'Provided data is empty'

if [[ -n "$TOKEN" ]]; then
    check_response "${BASE_URL%/}/roistat/crm.php?token=${TOKEN}&action=import_scheme" 200 '"statuses"'
fi
