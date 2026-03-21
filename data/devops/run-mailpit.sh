#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
ID_ROOT="/int/id"
COMPOSE_FILE="$ID_ROOT/docker-compose.yaml"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT_DIR/logs/devops/$TIMESTAMP"

DATA_DIR="${MAILPIT_DATA_DIR:-/var/lib/intdata/mailpit}"
CONFIG_DIR="${MAILPIT_CONFIG_DIR:-/etc/intdata/mailpit}"
LOG_DIR="${MAILPIT_LOG_DIR:-/var/log/intdata/mailpit}"
SMTP_USER="${MAILPIT_SMTP_USER:-${SMTP_USER:-intdata-smtp}}"
UI_USER="${MAILPIT_UI_USER:-intdata-ui}"
UI_PASSWORD="${MAILPIT_UI_PASSWORD:-}"

LOG_SCAN="${ROOT_DIR}/scripts/devops/log-scan.py"

mkdir -p "$REPORT_DIR"

ensure_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "ERROR: required command '%s' not found\n" "$1" >&2
    exit 1
  fi
}

ensure_command docker
ensure_command curl
ensure_command python3

printf "[mailpit] ensure host directories\n"
for dir in "$DATA_DIR" "$CONFIG_DIR" "$LOG_DIR"; do
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
  fi
done

AUTH_FILE="$CONFIG_DIR/users.htpasswd"
UI_AUTH_FILE="$CONFIG_DIR/ui.htpasswd"
TLS_DIR="$CONFIG_DIR/tls"

if [[ ! -f "$AUTH_FILE" ]]; then
  printf "WARNING: SMTP auth file %s not found; create with:\n" "$AUTH_FILE"
  printf "  htpasswd -bc %s %s <password>\n" "$AUTH_FILE" "$SMTP_USER"
fi

if [[ ! -f "$UI_AUTH_FILE" ]]; then
  printf "WARNING: UI auth file %s not found; create with:\n" "$UI_AUTH_FILE"
  printf "  htpasswd -bc %s %s <password>\n" "$UI_AUTH_FILE" "$UI_USER"
fi

if [[ ! -d "$TLS_DIR" ]]; then
  printf "WARNING: TLS dir %s not found; place certificates before production use.\n" "$TLS_DIR"
fi

for tls_path in \
  "$TLS_DIR/mail.intdata.pro.fullchain.pem" \
  "$TLS_DIR/mail.intdata.pro.privkey.pem" \
  "$TLS_DIR/smtp.intdata.pro.fullchain.pem" \
  "$TLS_DIR/smtp.intdata.pro.privkey.pem"
do
  if [[ ! -f "$tls_path" ]]; then
    printf "WARNING: TLS file missing: %s (create symlink to Let's Encrypt live cert).\n" "$tls_path"
  fi
done

printf "[mailpit] rebuild container\n"
docker compose -f "$COMPOSE_FILE" --profile mailpit up -d --build --remove-orphans

printf "[mailpit] restart stack\n"
docker compose -f "$COMPOSE_FILE" --profile mailpit up -d

printf "[mailpit] capture logs → %s\n" "$REPORT_DIR"
docker compose -f "$COMPOSE_FILE" --profile mailpit logs mailpit > "$REPORT_DIR/mailpit.log" 2>&1 || true

if [[ -f "$LOG_SCAN" ]]; then
  python3 "$LOG_SCAN" "$REPORT_DIR/mailpit.log" || true
fi

printf "[mailpit] smoke check mailpit info API\n"
set +e
if [[ -n "$UI_PASSWORD" ]]; then
  curl -skf -u "${UI_USER}:${UI_PASSWORD}" \
    --resolve mail.intdata.pro:8025:127.0.0.1 \
    https://mail.intdata.pro:8025/api/v1/info > "$REPORT_DIR/mailpit-info.json"
  SMOKE_STATUS=$?
else
  echo "WARNING: MAILPIT_UI_PASSWORD not set; performing unauthenticated smoke (may fail if auth enforced)." >&2
  curl -skf --resolve mail.intdata.pro:8025:127.0.0.1 \
    https://mail.intdata.pro:8025/api/v1/info > "$REPORT_DIR/mailpit-info.json"
  SMOKE_STATUS=$?
fi
set -e

if [[ $SMOKE_STATUS -ne 0 ]]; then
  printf "[mailpit] smoke FAILED (curl exit %d)\n" "$SMOKE_STATUS" >&2
  exit $SMOKE_STATUS
fi

printf "[mailpit] completed successfully\n"
