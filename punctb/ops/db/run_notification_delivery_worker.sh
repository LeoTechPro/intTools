#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ENV file not found: ${ENV_FILE}" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

BASE_URL="${API_BASE_URL:-${SUPABASE_PUBLIC_URL:-https://api-dev.punctb.pro}}"
BASE_URL="${BASE_URL%/}"
TOKEN="${SERVICE_ROLE_KEY:-${SUPABASE_SERVICE_ROLE_KEY:-}}"
ATTEMPTS="${DELIVERY_WORKER_ATTEMPTS:-6}"
RETRY_DELAY_SEC="${DELIVERY_WORKER_RETRY_DELAY_SEC:-2}"

if [[ -z "${TOKEN}" ]]; then
  echo "SERVICE_ROLE_KEY is not configured in ${ENV_FILE}" >&2
  exit 1
fi

if ! [[ "${ATTEMPTS}" =~ ^[0-9]+$ ]] || (( ATTEMPTS < 1 )); then
  ATTEMPTS=6
fi

if ! [[ "${RETRY_DELAY_SEC}" =~ ^[0-9]+$ ]] || (( RETRY_DELAY_SEC < 0 )); then
  RETRY_DELAY_SEC=2
fi

for ((attempt=1; attempt<=ATTEMPTS; attempt++)); do
  if curl -sS --fail-with-body \
    -X POST "${BASE_URL}/functions/v1/notification-delivery-worker?limit=20" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "apikey: ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{}' >/dev/null; then
    echo "notification-delivery-worker: ok $(date -u +%FT%TZ) (attempt ${attempt}/${ATTEMPTS})"
    exit 0
  fi

  if (( attempt < ATTEMPTS )); then
    sleep "${RETRY_DELAY_SEC}"
  fi
done

echo "notification-delivery-worker: failed after ${ATTEMPTS} attempts" >&2
exit 1
