#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  openclaw-intbrain-query.sh --owner <owner_id> "<query>"
  INTBRAIN_OWNER_ID=42 openclaw-intbrain-query.sh "<query>"
EOF
  exit 64
}

OWNER_ID="${INTBRAIN_OWNER_ID:-}"
if [[ "${1:-}" == "--owner" ]]; then
  shift
  [[ $# -ge 2 ]] || usage
  OWNER_ID="$1"
  shift
fi

[[ $# -ge 1 ]] || usage
QUERY="$*"

if [[ -z "$OWNER_ID" ]]; then
  echo "openclaw-intbrain-query: owner id is required (--owner or INTBRAIN_OWNER_ID)" >&2
  exit 64
fi

if [[ -z "${INTBRAIN_AGENT_ID:-}" || -z "${INTBRAIN_AGENT_KEY:-}" ]]; then
  ENV_FILE="${INTBRAIN_ENV_FILE:-/int/tools/.runtime/codex-secrets/intbrain-agent.env}"
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
fi

if [[ -z "${INTBRAIN_AGENT_ID:-}" || -z "${INTBRAIN_AGENT_KEY:-}" ]]; then
  echo "openclaw-intbrain-query: missing INTBRAIN_AGENT_ID/INTBRAIN_AGENT_KEY" >&2
  exit 78
fi

API_BASE="${INTBRAIN_API_BASE_URL:-https://brain.api.intdata.pro/api/core/v1}"
WORKDIR="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"

if [[ ! -d "$WORKDIR" ]]; then
  echo "openclaw-intbrain-query: workspace not found: $WORKDIR" >&2
  exit 66
fi

QUERY_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$QUERY")"

CONTEXT_JSON="$(curl -fsS \
  -X POST "${API_BASE%/}/context/pack" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "X-Agent-Id: ${INTBRAIN_AGENT_ID}" \
  -H "X-Agent-Key: ${INTBRAIN_AGENT_KEY}" \
  --data "$(printf '{"owner_id":%s,"query":%s,"limit":20,"depth":2}' "$OWNER_ID" "$QUERY_JSON")")"

PROMPT=$(cat <<EOF
Ты отвечаешь как универсальный агент с memory-core intbrain.
Используй intbrain context pack как основной источник.
Если в context pack явно указано fallback_needed=true, сообщи, что нужен markdown fallback.
Не раскрывай секреты и внутренние токены.

Context pack (JSON):
${CONTEXT_JSON}

Запрос пользователя:
${QUERY}
EOF
)

exec codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  -C "${WORKDIR}" \
  "${PROMPT}"
