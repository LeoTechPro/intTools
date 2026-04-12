#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

DB_NAME="${POSTGRES_DB:-}"
if [[ -z "${DB_NAME}" && -f "${REPO_ROOT}/.env.example" ]]; then
  DB_NAME="$(grep -E '^POSTGRES_DB=' "${REPO_ROOT}/.env.example" | tail -n1 | cut -d= -f2- | tr -d '[:space:]')"
fi
DB_NAME="${DB_NAME:-intdata}"

QUEUE_LAG_THRESHOLD_MIN="${QUEUE_LAG_THRESHOLD_MIN:-15}"
FAIL_WINDOW_MIN="${FAIL_WINDOW_MIN:-15}"
FAIL_RATE_THRESHOLD_PCT="${FAIL_RATE_THRESHOLD_PCT:-30}"
FAIL_RATE_MIN_TOTAL="${FAIL_RATE_MIN_TOTAL:-5}"
AUTH_TIMEOUT_WINDOW_MIN="${AUTH_TIMEOUT_WINDOW_MIN:-15}"
AUTH_TIMEOUT_THRESHOLD="${AUTH_TIMEOUT_THRESHOLD:-1}"
AUTH_CONTAINER="${AUTH_CONTAINER:-$(cd "${REPO_ROOT}" && docker compose ps -q auth 2>/dev/null || true)}"

queue_lag_min="$(sudo -u postgres psql -d "${DB_NAME}" -At -v ON_ERROR_STOP=1 -c "
  SELECT COALESCE(MAX(EXTRACT(EPOCH FROM (now() - nd.created_at)) / 60.0), 0)
  FROM app.event_notification_deliveries nd
  WHERE nd.channel_code = 'email'
    AND nd.status = 'queued';
")"

failed_and_total="$(sudo -u postgres psql -d "${DB_NAME}" -At -v ON_ERROR_STOP=1 -c "
  SELECT
    COALESCE(SUM((nd.status = 'failed')::int), 0) AS failed,
    COALESCE(SUM((nd.status IN ('failed', 'sent'))::int), 0) AS total
  FROM app.event_notification_deliveries nd
  WHERE nd.channel_code = 'email'
    AND nd.updated_at >= now() - make_interval(mins => ${FAIL_WINDOW_MIN});
")"

failed_count="${failed_and_total%%|*}"
total_count="${failed_and_total##*|}"

fail_rate_pct="0"
if [[ "${total_count}" =~ ^[0-9]+$ ]] && [[ "${failed_count}" =~ ^[0-9]+$ ]] && (( total_count > 0 )); then
  fail_rate_pct="$(awk -v f="${failed_count}" -v t="${total_count}" 'BEGIN { printf "%.2f", (f*100.0)/t }')"
fi

auth_timeout_count="0"
if [[ -n "${AUTH_CONTAINER}" ]]; then
  auth_timeout_count="$(docker logs --since "${AUTH_TIMEOUT_WINDOW_MIN}m" "${AUTH_CONTAINER}" 2>&1 \
    | rg -c '"error_code":"request_timeout"|"status":504|Processing this request timed out' || true)"
fi
auth_timeout_count="${auth_timeout_count:-0}"
if [[ ! "${auth_timeout_count}" =~ ^[0-9]+$ ]]; then
  auth_timeout_count="0"
fi

declare -a alerts=()

if awk -v lag="${queue_lag_min}" -v thr="${QUEUE_LAG_THRESHOLD_MIN}" 'BEGIN { exit !(lag > thr) }'; then
  alerts+=("queue_lag=${queue_lag_min}m > ${QUEUE_LAG_THRESHOLD_MIN}m")
fi

if [[ "${total_count}" =~ ^[0-9]+$ ]] && (( total_count >= FAIL_RATE_MIN_TOTAL )); then
  if awk -v rate="${fail_rate_pct}" -v thr="${FAIL_RATE_THRESHOLD_PCT}" 'BEGIN { exit !(rate > thr) }'; then
    alerts+=("delivery_fail_rate=${fail_rate_pct}% > ${FAIL_RATE_THRESHOLD_PCT}% (failed=${failed_count}, total=${total_count}, window=${FAIL_WINDOW_MIN}m)")
  fi
fi

if [[ "${auth_timeout_count}" =~ ^[0-9]+$ ]] && (( auth_timeout_count >= AUTH_TIMEOUT_THRESHOLD )); then
  alerts+=("auth_request_timeout=${auth_timeout_count} >= ${AUTH_TIMEOUT_THRESHOLD} (window=${AUTH_TIMEOUT_WINDOW_MIN}m)")
fi

echo "delivery-health: db=${DB_NAME} queue_lag_min=${queue_lag_min} fail_rate_pct=${fail_rate_pct} failed=${failed_count} total=${total_count} auth_timeout=${auth_timeout_count}"

if (( ${#alerts[@]} > 0 )); then
  echo "delivery-health: ALERT"
  for item in "${alerts[@]}"; do
    echo " - ${item}"
  done
  exit 1
fi

echo "delivery-health: OK"
