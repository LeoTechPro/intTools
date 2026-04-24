#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[local-redeploy] %s\n' "$*"
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BRAIN_REPO_ROOT="${BRAIN_REPO_ROOT:-/int/brain}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
REPORT_ROOT="$ROOT/logs/devops/$TIMESTAMP"
mkdir -p "$REPORT_ROOT"

LOG_SCAN="$ROOT/delivery/devops/log-scan.py"
PATTERN_LABELS='ERROR|FATAL|CRITICAL|Traceback|Unhandled|panic|OOM|bind: address already in use|Migrations failed|connection refused'

CANDIDATE_SYSTEMD_UNITS=("intdata-web" "intdata-web-dev" "nexus-intdata-web" "nexus-intdata-web-dev" "intdata-worker" "nexus-intdata-worker")
if [[ -n "${INTDATA_SYSTEMD_UNITS:-}" ]]; then
  # shellcheck disable=SC2206
  CANDIDATE_SYSTEMD_UNITS=(${INTDATA_SYSTEMD_UNITS})
fi

compose_files=()
while IFS= read -r file; do
  compose_files+=("$file")
done < <(find "$ROOT" -maxdepth 1 -type f -name 'docker-compose*.yml' -print)

active_systemd_units=()
if command -v systemctl >/dev/null 2>&1; then
  for unit in "${CANDIDATE_SYSTEMD_UNITS[@]}"; do
    [[ -z "$unit" ]] && continue
    if systemctl list-unit-files --no-legend 2>/dev/null | grep -q "^${unit}\.service"; then
      active_systemd_units+=("$unit")
    elif systemctl list-units --all --no-legend 2>/dev/null | grep -q "${unit}\.service"; then
      active_systemd_units+=("$unit")
    fi
  done
fi

MODE="fallback"
if (( ${#compose_files[@]} )); then
  MODE="compose"
elif (( ${#active_systemd_units[@]} )); then
  MODE="systemd"
fi

log "Определён режим: $MODE"

status=0
summary=()
add_summary() {
  summary+=("$1")
}

run_cmd() {
  local description="$1"
  shift
  log "$description"
  if "$@"; then
    add_summary "✔ $description"
  else
    add_summary "✖ $description"
    status=1
  fi
}

compose_args=()
if [[ "$MODE" == "compose" ]]; then
  for file in "${compose_files[@]}"; do
    compose_args+=(-f "$file")
  done
fi

compose_services=()
if [[ "$MODE" == "compose" ]]; then
  if docker compose "${compose_args[@]}" config --services >"$REPORT_ROOT/compose-services.txt" 2>"$REPORT_ROOT/compose-config.err"; then
    mapfile -t compose_services <"$REPORT_ROOT/compose-services.txt"
  else
    add_summary "✖ Не удалось получить список сервисов compose"
    status=1
  fi
  if (( ${#compose_services[@]} )); then
    run_cmd "Rebuild (compose)" docker compose "${compose_args[@]}" build --pull "${compose_services[@]}"
  else
    run_cmd "Rebuild (compose)" docker compose "${compose_args[@]}" build --pull
  fi
  run_cmd "Restart (compose)" docker compose "${compose_args[@]}" up -d --force-recreate --remove-orphans
elif [[ "$MODE" == "systemd" ]]; then
  if [[ -f "$ROOT/requirements.txt" ]]; then
    run_cmd "Обновление Python-зависимостей" python3 -m pip install -r "$ROOT/requirements.txt"
  elif [[ -f "$ROOT/pyproject.toml" ]]; then
    run_cmd "Обновление Python-зависимостей" python3 -m pip install "$ROOT"
  fi
  if [[ -f "$BRAIN_REPO_ROOT/web/package.json" ]]; then
    run_cmd "npm install (nexus web)" npm install --prefix "$BRAIN_REPO_ROOT/web"
    run_cmd "npm build (nexus web)" npm run --prefix "$BRAIN_REPO_ROOT/web" build
  fi
  for unit in "${active_systemd_units[@]}"; do
    run_cmd "Restart systemd unit $unit" sudo -n systemctl restart "$unit"
  done
else
  if [[ -x "$ROOT/delivery/devops/rebuild_service.sh" ]]; then
    run_cmd "Fallback rebuild_service.sh" "$ROOT/delivery/devops/rebuild_service.sh"
  else
    add_summary "✖ Fallback: отсутствует delivery/devops/rebuild_service.sh"
    status=1
  fi
fi

log_files=()
if [[ "$MODE" == "compose" ]]; then
  targets=("${compose_services[@]}")
  if (( ! ${#targets[@]} )); then
    if docker compose "${compose_args[@]}" ps --services >"$REPORT_ROOT/compose-ps.txt" 2>"$REPORT_ROOT/compose-ps.err"; then
      mapfile -t targets <"$REPORT_ROOT/compose-ps.txt"
    fi
  fi
  for svc in "${targets[@]}"; do
    [[ -z "$svc" ]] && continue
    logfile="$REPORT_ROOT/${svc}.log"
    if docker compose "${compose_args[@]}" logs --no-color --tail=400 "$svc" >"$logfile" 2>&1; then
      log_files+=("$logfile")
    else
      add_summary "✖ Не удалось собрать логи compose для $svc"
      status=1
    fi
  done
elif [[ "$MODE" == "systemd" ]]; then
  for unit in "${active_systemd_units[@]}"; do
    logfile="$REPORT_ROOT/${unit}.log"
    if sudo -n journalctl -u "$unit" -n 400 --no-pager >"$logfile" 2>&1; then
      log_files+=("$logfile")
    else
      add_summary "✖ Не удалось собрать логи systemd для $unit"
      status=1
    fi
  done
else
  if [[ -d "$ROOT/var/logs" ]]; then
    while IFS= read -r file; do
      [[ -z "$file" ]] && continue
      logfile="$REPORT_ROOT/$(basename "$file")"
      if tail -n 400 "$file" >"$logfile" 2>/dev/null; then
        log_files+=("$logfile")
      fi
    done < <(find "$ROOT/var/logs" -maxdepth 1 -type f)
  fi
fi

if [[ -x "$LOG_SCAN" ]]; then
  for file in "${log_files[@]}"; do
    [[ -f "$file" ]] || continue
    scan_out="${file%.log}.scan"
    if python3 "$LOG_SCAN" "$file" "$PATTERN_LABELS" >"$scan_out" 2>&1; then
      add_summary "✔ Логи без критических ошибок: $(basename "$file")"
    else
      add_summary "✖ Критические ошибки в логах: $(basename "$file")"
      status=1
    fi
  done
else
  add_summary "✖ log-scan.py не найден или не исполняем"
  status=1
fi

SMOKE_URLS=()
if [[ -n "${DEVOPS_SMOKE_URLS:-}" ]]; then
  # shellcheck disable=SC2206
  SMOKE_URLS=(${DEVOPS_SMOKE_URLS})
fi
if (( ${#SMOKE_URLS[@]} )); then
  SMOKE_FILE="$REPORT_ROOT/smoke.txt"
  : >"$SMOKE_FILE"
  for url in "${SMOKE_URLS[@]}"; do
    start=$(date +%s%3N)
    http_line=$(curl -kfsS -w "%{http_code} %{time_total}" -o /dev/null "$url" 2>&1) || true
    end=$(date +%s%3N)
    printf '%s %s %s %sms\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$url" "$http_line" "$((end-start))" >>"$SMOKE_FILE"
    if [[ "$http_line" =~ ^2 ]]; then
      add_summary "✔ Smoke ${url}"
    else
      add_summary "✖ Smoke ${url}"
      status=1
    fi
  done
else
  add_summary "ℹ Smoke не настроен: переменная DEVOPS_SMOKE_URLS пуста"
fi

SUMMARY_FILE="$REPORT_ROOT/summary.txt"
printf 'DevOps run (UTC): %s\n' "$TIMESTAMP" >"$SUMMARY_FILE"
for line in "${summary[@]}"; do
  printf '%s\n' "$line" >>"$SUMMARY_FILE"
done

log "Сводка сохранена: $SUMMARY_FILE"
exit "$status"
