#!/usr/bin/env bash
set -euo pipefail

MIN_AGE_SECONDS="${MIN_AGE_SECONDS:-900}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
LOCK_FILE="${CODEX_HOME}/tmp/probe-agent-orphan-cleaner.lock"
LOG_FILE="${CODEX_HOME}/log/probe-agent-orphan-cleaner.log"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

mkdir -p "$(dirname "$LOCK_FILE")" "$(dirname "$LOG_FILE")"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  exit 0
fi

match_target_cmd() {
  local cmd="$1"
  [[ "$cmd" == *"agent-browser/bin/"*"/dist/daemon.js"* ]] && return 0
  [[ "$cmd" == *"chrome-headless-shell"* ]] && return 0
  [[ "$cmd" == *"npm exec @modelcontextprotocol/server-filesystem"* ]] && return 0
  [[ "$cmd" == *"npm exec @playwright/mcp"* ]] && return 0
  [[ "$cmd" == *"mcp-server-postgres"* ]] && return 0
  [[ "$cmd" == *"mcp-server-github"* ]] && return 0
  [[ "$cmd" == *"mcp-server-filesystem"* ]] && return 0
  [[ "$cmd" == *"playwright-mcp"* ]] && return 0
  return 1
}

PIDS=()
while read -r PID PARENT_PID ETIMES STAT CMD; do
  [[ -z "${PID:-}" ]] && continue
  [[ "$PARENT_PID" != "1" ]] && continue
  (( ETIMES >= MIN_AGE_SECONDS )) || continue
  [[ "$STAT" == Z* ]] && continue

  if match_target_cmd "$CMD"; then
    PIDS+=("$PID")
  fi
done < <(ps -eo pid=,ppid=,etimes=,stat=,cmd=)

TS="$(date -Is)"

if (( ${#PIDS[@]} == 0 )); then
  echo "$TS no_orphans_found" >> "$LOG_FILE"
  exit 0
fi

if (( DRY_RUN == 1 )); then
  echo "$TS dry_run candidates=${#PIDS[@]} pids=${PIDS[*]}" | tee -a "$LOG_FILE"
  ps -o pid=,ppid=,etimes=,stat=,cmd= -p "$(IFS=,; echo "${PIDS[*]}")"
  exit 0
fi

kill -TERM "${PIDS[@]}" 2>/dev/null || true
sleep 2

SURVIVORS=()
for PID in "${PIDS[@]}"; do
  if kill -0 "$PID" 2>/dev/null; then
    SURVIVORS+=("$PID")
  fi
done

if (( ${#SURVIVORS[@]} > 0 )); then
  kill -KILL "${SURVIVORS[@]}" 2>/dev/null || true
  sleep 1
fi

ALIVE=0
for PID in "${PIDS[@]}"; do
  if kill -0 "$PID" 2>/dev/null; then
    ALIVE=$((ALIVE + 1))
  fi
done

echo "$TS cleaned=${#PIDS[@]} forced=${#SURVIVORS[@]} still_alive=$ALIVE" >> "$LOG_FILE"
