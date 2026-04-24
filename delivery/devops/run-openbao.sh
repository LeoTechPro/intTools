#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ID_ROOT="/int/id"
COMPOSE_FILE="$ID_ROOT/docker-compose.yaml"
ROOT_ENV_FILE="$ROOT_DIR/.env"
ID_ENV_FILE="$ID_ROOT/.env"

if [[ -n "${OPENBAO_ENV_FILE:-}" ]]; then
  ENV_FILE="${OPENBAO_ENV_FILE}"
else
  if [[ -f "$ROOT_ENV_FILE" ]]; then
    ENV_FILE="$ROOT_ENV_FILE"
  elif [[ -f "$ID_ENV_FILE" ]]; then
    ENV_FILE="$ID_ENV_FILE"
  else
    ENV_FILE="$ROOT_ENV_FILE"
  fi
fi
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT_DIR/logs/devops/$TIMESTAMP"

mkdir -p "$REPORT_DIR"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERROR: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Синхронизируйте секреты командой \`python3 -m api.cli sync-openbao\` из /int/id или создайте файл по шаблону /int/id/.env.example" >&2
  exit 1
fi

ensure_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command '$1' not found in PATH" >&2
    exit 1
  fi
}

ensure_cmd docker
ensure_cmd curl

get_env() {
  local key="$1"
  local default_value="$2"
  local env_value="${!key-}"
  if [[ -n "$env_value" ]]; then
    echo "$env_value"
    return
  fi
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d'=' -f2- || true)"
  if [[ -z "$line" ]]; then
    echo "$default_value"
    return
  fi
  line="${line%\"}"
  line="${line#\"}"
  line="${line%\'}"
  line="${line#\'}"
  echo "$line"
}

HTTP_PORT="$(get_env OPENBAO_HTTP_PORT 8200)"
ROOT_TOKEN="$(get_env OPENBAO_ROOT_TOKEN root-token)"

export OPENBAO_ENV_FILE="$ENV_FILE"

echo "[openbao] compose up (build)"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile openbao up -d --build --remove-orphans

echo "[openbao] capture logs → $REPORT_DIR"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile openbao logs openbao > "$REPORT_DIR/openbao.log" 2>&1 || true

LOG_SCAN="$ROOT_DIR/delivery/devops/log-scan.py"
if [[ -f "$LOG_SCAN" ]]; then
  python3 "$LOG_SCAN" "$REPORT_DIR/openbao.log" || true
fi

HEALTH_URL="http://127.0.0.1:${HTTP_PORT}/v1/sys/health?standbyok=true&perfstandbyok=true"

set +e
curl -fsS "$HEALTH_URL" -H "X-Vault-Token: ${ROOT_TOKEN}" > "$REPORT_DIR/openbao-health.json"
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo "[openbao] health check failed (curl exit $STATUS)" >&2
  exit $STATUS
fi

echo "[openbao] completed successfully"
