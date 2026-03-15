#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: openclaw-bitrix-query.sh '<query>'" >&2
  exit 64
fi

QUERY="$*"
WORKDIR="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"

if [[ ! -d "$WORKDIR" ]]; then
  echo "openclaw-bitrix-query: workspace not found: $WORKDIR" >&2
  exit 66
fi

PROMPT=$(cat <<EOF
Ты выполняешь запрос к Bitrix24 для OpenClaw.
Обязательно используй MCP-сервер bitrix24 как основной источник данных.
Тебе разрешены как чтение, так и изменения данных в Bitrix24.
Любые мутации выполняй только если в самом запросе пользователя есть прямая и однозначная команда что-то создать, обновить, переместить или иным образом изменить.
Если запрос на изменение неоднозначен, сначала верни, что именно нужно подтвердить.
Если для ответа не хватает данных, так и скажи.
Ответ дай кратко, по-русски, без раскрытия секретов.

Запрос пользователя:
${QUERY}
EOF
)

exec codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  -C "${WORKDIR}" \
  "${PROMPT}"
