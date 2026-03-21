#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NEXUS_REPO_ROOT="${NEXUS_REPO_ROOT:-/int/nexus}"
EXPECTED_BRANCH="dev"
PATTERN='ERROR|FATAL|CRITICAL|Traceback|Unhandled|panic|OOM|bind: address already in use|Migrations failed|connection refused'
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$REPO_ROOT/logs/devops/$TIMESTAMP"
SUMMARY_FILE="$REPORT_DIR/summary.txt"

mkdir -p "$REPORT_DIR"

current_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "$EXPECTED_BRANCH" ]]; then
  echo "ERROR: dev-redeploy.sh must run on branch $EXPECTED_BRANCH (current: $current_branch)." >&2
  exit 1
fi

load_env_file() {
  local file="$1"
  [[ ! -f "$file" ]] && return
  if command -v python3 >/dev/null 2>&1; then
    eval "$(python3 - "$file" <<'PY'
import sys, shlex, pathlib

path = pathlib.Path(sys.argv[1])
if not path.exists():
    sys.exit(0)

for raw in path.read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith('#'):
        continue
    if '=' not in raw:
        continue
    key, value = raw.split('=', 1)
    key = key.strip()
    if not key:
        continue
    value = value.rstrip()
    stripped = value.strip()
    if stripped.startswith(('"', "'")) and stripped.endswith(stripped[0]) and len(stripped) >= 2:
        stripped = stripped[1:-1]
    else:
        hash_index = stripped.find(' #')
        if hash_index != -1:
            stripped = stripped[:hash_index].rstrip()
    print(f"export {key}={shlex.quote(stripped)}")
PY
)"
  else
    echo "WARN: python3 отсутствует, пропускаю загрузку переменных из $file" >&2
  fi
}

load_env_file "$REPO_ROOT/.env"

if [[ -z "${ENV_FILE:-}" ]]; then
  if [[ -f "$NEXUS_REPO_ROOT/.env" ]]; then
    ENV_FILE="$NEXUS_REPO_ROOT/.env"
    export ENV_FILE
  fi
fi

if [[ -n "${ENV_FILE:-}" ]]; then
  if [[ -f "$ENV_FILE" && "$ENV_FILE" != "$REPO_ROOT/.env" ]]; then
    load_env_file "$ENV_FILE"
  fi
fi

log_files=()
critical=0

compose_args=()
compose_profiles_list=()
if [[ -n "${DEVOPS_COMPOSE_FILES:-}" ]]; then
  IFS=',' read -ra _compose_files <<< "$DEVOPS_COMPOSE_FILES"
  for file in "${_compose_files[@]}"; do
    file="$(echo "$file" | xargs)"
    [[ -z "$file" ]] && continue
    [[ -f "$REPO_ROOT/$file" ]] && compose_args+=("-f" "$file")
  done
  if [[ -n "${DEVOPS_COMPOSE_PROFILES:-}" ]]; then
    IFS=',' read -ra _profiles <<< "$DEVOPS_COMPOSE_PROFILES"
    for profile in "${_profiles[@]}"; do
      profile="$(echo "$profile" | xargs)"
      [[ -z "$profile" ]] && continue
      compose_profiles_list+=("$profile")
    done
  fi
fi

units=(intdata-web-dev nexus-intdata-web-dev bot-intdata-dev intdata-worker-dev)
available=()
for unit in "${units[@]}"; do
  if systemctl list-unit-files "$unit" >/dev/null 2>&1 || systemctl status "$unit" >/dev/null 2>&1; then
    available+=("$unit")
  fi
done

if [[ "${DEVOPS_SKIP_SYSTEMD:-0}" == "1" ]]; then
  available=()
fi

run_compose() {
  local -n _args=$1
  local -n _profiles=$2
  local compose_profiles=""
  if [[ ${#_profiles[@]} -gt 0 ]]; then
    compose_profiles=$(IFS=','; echo "${_profiles[*]}")
  fi
  {
    echo "[compose] docker compose ${_args[*]} build --pull"
    if [[ -n "$compose_profiles" ]]; then
      COMPOSE_PROFILES="$compose_profiles" docker compose "${_args[@]}" build --pull
    else
      docker compose "${_args[@]}" build --pull
    fi
    echo "[compose] docker compose ${_args[*]} up -d --force-recreate --remove-orphans"
    if [[ -n "$compose_profiles" ]]; then
      COMPOSE_PROFILES="$compose_profiles" docker compose "${_args[@]}" up -d --force-recreate --remove-orphans
    else
      docker compose "${_args[@]}" up -d --force-recreate --remove-orphans
    fi
  } >>"$SUMMARY_FILE" 2>&1 || critical=1

  if [[ -n "$compose_profiles" ]]; then
    services="$(COMPOSE_PROFILES="$compose_profiles" docker compose "${_args[@]}" ps --services 2>/dev/null || true)"
    if [[ -z "$services" ]]; then
      services="$(COMPOSE_PROFILES="$compose_profiles" docker compose "${_args[@]}" config --services 2>/dev/null || true)"
    fi
  else
    services="$(docker compose "${_args[@]}" ps --services 2>/dev/null || true)"
    if [[ -z "$services" ]]; then
      services="$(docker compose "${_args[@]}" config --services 2>/dev/null || true)"
    fi
  fi
  if [[ -n "$services" ]]; then
    while IFS= read -r svc; do
      [[ -z "$svc" ]] && continue
      log_file="$REPORT_DIR/${svc}.log"
      if [[ -n "$compose_profiles" ]]; then
        COMPOSE_PROFILES="$compose_profiles" docker compose "${_args[@]}" logs --no-color --tail 400 "$svc" >"$log_file" 2>&1 || true
      else
        docker compose "${_args[@]}" logs --no-color --tail 400 "$svc" >"$log_file" 2>&1 || true
      fi
      log_files+=("$log_file")
    done <<< "$services"
  fi
}

if [[ ${#compose_args[@]} -gt 0 ]]; then
  run_compose compose_args compose_profiles_list
elif [[ ${#available[@]} -gt 0 ]]; then
  for unit in "${available[@]}"; do
    echo "[systemd] sudo -n systemctl restart $unit" >>"$SUMMARY_FILE"
    if ! sudo -n systemctl restart "$unit" >>"$SUMMARY_FILE" 2>&1; then
      critical=1
      echo "[systemd] restart $unit failed (sudo -n)" >>"$SUMMARY_FILE"
    fi
    journalctl -u "$unit" -n 400 --no-pager >"$REPORT_DIR/${unit}.log" 2>&1 || true
    log_files+=("$REPORT_DIR/${unit}.log")
  done
else
  auto_compose=()
  while IFS= read -r file; do
    rel="${file#./}"
    auto_compose+=("-f" "$rel")
  done < <(cd "$REPO_ROOT" && find . -maxdepth 2 -type f \( -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' -o -name '*compose*.yml' -o -name '*compose*.yaml' \))
  if [[ ${#auto_compose[@]} -gt 0 ]]; then
    run_compose auto_compose compose_profiles_list
  elif [[ -x "$REPO_ROOT/scripts/devops/local-redeploy.sh" ]]; then
    "$REPO_ROOT/scripts/devops/local-redeploy.sh" restart >>"$SUMMARY_FILE" 2>&1 || critical=1
  else
    echo "ERROR: runtime autodetect failed (no docker compose files or systemd units)." >&2
    exit 1
  fi
fi

smoke_urls=()
smoke_file="$REPORT_DIR/smoke.txt"
smoke_wait="${SMOKE_WAIT_SECONDS:-5}"
if [[ "$smoke_wait" =~ ^[0-9]+$ ]] && [[ "$smoke_wait" -gt 0 ]]; then
  sleep "$smoke_wait"
fi
if [[ -n "${SMOKE_URLS:-}" ]]; then
  IFS=',' read -ra _urls <<< "$SMOKE_URLS"
  for url in "${_urls[@]}"; do
    url="$(echo "$url" | xargs)"
    [[ -z "$url" ]] && continue
    smoke_urls+=("$url")
  done
else
  if [[ -n "${PUBLIC_URL:-}" ]]; then
    smoke_urls+=("${PUBLIC_URL%/}/healthz")
  fi
  if [[ -n "${API_URL:-}" ]]; then
    smoke_urls+=("${API_URL%/}/healthz")
  fi
fi

if [[ ${#smoke_urls[@]} -gt 0 ]]; then
  : >"$smoke_file"
  for url in "${smoke_urls[@]}"; do
    [[ -z "$url" ]] && continue
    echo "== $url ==" >>"$smoke_file"
    if curl -kfsS --max-time 10 "$url" >>"$smoke_file" 2>&1; then
      printf "\n[OK]\n\n" >>"$smoke_file"
    else
      printf "\n[FAIL]\n\n" >>"$smoke_file"
      critical=1
    fi
  done
fi

smoke_script="$REPO_ROOT/scripts/devops/smoke.sh"
if [[ -x "$smoke_script" ]]; then
  smoke_script_log="$REPORT_DIR/smoke-script.log"
  if "$smoke_script" >"$smoke_script_log" 2>&1; then
    :
  else
    critical=1
  fi
fi

for log_file in "${log_files[@]}"; do
  [[ ! -s "$log_file" ]] && continue
  if grep -E "$PATTERN" "$log_file" >"${log_file%.log}.errors.log"; then
    critical=1
  else
    rm -f "${log_file%.log}.errors.log"
  fi
done

echo "Reports directory: $REPORT_DIR"

if [[ $critical -ne 0 ]]; then
  echo "ERROR: critical issues detected, see $REPORT_DIR." >&2
  exit 1
fi

echo "OK: dev environment refreshed (branch $EXPECTED_BRANCH)."
