#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: openclaw-bizon-query.sh '<query>'" >&2
  exit 64
fi

QUERY="$*"
WORKDIR="${OPENCLAW_BIZON_WORKDIR:-/int/crm}"

PROMPT=$(cat <<EOF
Ты выполняешь запрос к Bizon365 для OpenClaw.
Обязательно используй MCP-сервер bizon365 как основной источник данных.
Для вебинаров, комнат, сотрудников, файлов диска и записей сначала используй typed-tools Bizon365 MCP.
Если запись или чат старого вебинара не находятся в live-данных Bizon365, используй архивный fallback через Bizon365 MCP, который читает Яндекс Диск.
Тебе разрешены как чтение, так и изменения данных в Bizon365, но любые мутации выполняй только если в самом запросе пользователя есть прямая и однозначная команда что-то изменить.
Если запрос на изменение неоднозначен, сначала верни, что именно нужно подтвердить.
Если для ответа не хватает данных, так и скажи.
Ответ дай кратко, по-русски, без раскрытия секретов.

Запрос пользователя:
${QUERY}
EOF
)

export BIZON365_MCP_CLIENT_PROFILE=openclaw

exec codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  -C "${WORKDIR}" \
  "${PROMPT}"
