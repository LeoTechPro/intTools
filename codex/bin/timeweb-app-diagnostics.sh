#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
# shellcheck source=../lib/codex-env.sh
source "$ROOT_DIR/lib/codex-env.sh"

env_name="timeweb-cloud.env"
API_BASE_URL="https://api.timeweb.cloud/api/v1"
codex_source_env_file "$env_name" || true

if [[ -z "${TIMEWEB_TOKEN:-}" ]]; then
  cat >&2 <<EOF
TIMEWEB_TOKEN is not set.
Set it in $(codex_primary_env_hint "$env_name") before using this helper.
EOF
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

usage() {
  cat <<'EOF'
Usage:
  timeweb-app-diagnostics.sh list
  timeweb-app-diagnostics.sh app APP_ID
  timeweb-app-diagnostics.sh deploys APP_ID
  timeweb-app-diagnostics.sh logs APP_ID [LIMIT]
EOF
}

api_get() {
  local path="$1"
  curl -fsS --max-time 30 \
    -H "Authorization: Bearer ${TIMEWEB_TOKEN}" \
    "${API_BASE_URL}${path}"
}

cmd="${1:-}"

case "$cmd" in
  list)
    api_get "/apps" | jq '{
      apps: (.apps // [])
        | map({
            id,
            name,
            status,
            type,
            domain: ((.domains // [])[0].fqdn // null),
            branch,
            project_id
          })
    }'
    ;;
  app)
    app_id="${2:-}"
    [[ -n "$app_id" ]] || { usage >&2; exit 1; }
    api_get "/apps/${app_id}" | jq '.app'
    ;;
  deploys)
    app_id="${2:-}"
    [[ -n "$app_id" ]] || { usage >&2; exit 1; }
    api_get "/apps/${app_id}/deploys" | jq '{
      deploys: (.deploys // [])
        | map({
            id,
            status,
            started_at,
            ended_at,
            commit_sha,
            commit_msg
          })
    }'
    ;;
  logs)
    app_id="${2:-}"
    limit="${3:-50}"
    [[ -n "$app_id" ]] || { usage >&2; exit 1; }
    api_get "/apps/${app_id}/logs?limit=${limit}" | jq '.'
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
