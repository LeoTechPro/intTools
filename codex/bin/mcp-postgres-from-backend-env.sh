#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/int/assess/backend/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "MCP postgres: missing $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:?DB_PORT is required}"

export PGPASSWORD="$POSTGRES_PASSWORD"
exec npx -y @modelcontextprotocol/server-postgres "postgresql://${POSTGRES_USER}@${DB_HOST}:${DB_PORT}/${POSTGRES_DB}"
