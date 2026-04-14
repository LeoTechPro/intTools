#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Resolve logical SSH target for /int transport layer.

Usage:
  int_ssh_host.sh --logical <dev-intdata|dev-codex|dev-openclaw|prod-leon> [--mode auto|tailnet|public]

Output:
  destination to stdout
  selected metadata JSON to stderr
USAGE
}

logical=""
mode="${INT_SSH_MODE:-auto}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --logical)
      logical="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "int_ssh_host.sh: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$logical" ]]; then
  echo "int_ssh_host.sh: --logical is required" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
engine="${script_dir}/int_ssh_resolve.py"

if [[ ! -f "$engine" ]]; then
  echo "int_ssh_host.sh: resolver engine not found: $engine" >&2
  exit 2
fi

python_bin="${PYTHON_BIN:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  elif command -v python >/dev/null 2>&1; then
    python_bin="python"
  else
    echo "int_ssh_host.sh: python runtime is required" >&2
    exit 2
  fi
fi

payload="$("$python_bin" "$engine" --requested-host "$logical" --mode "$mode" --json)"
destination="$("$python_bin" -c 'import json,sys; print(json.loads(sys.stdin.read())["destination"])' <<<"$payload")"

echo "$destination"
echo "$payload" >&2
