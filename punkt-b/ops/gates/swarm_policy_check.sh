#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

MATRIX_FILE="templates/swarm-risk-matrix.yaml"
MATRIX_HELPER=""
FILES_ARG=""
COMPLETED_CHECKS=""
MODE="hard"
EXCEPTION_FILE=""

usage() {
  cat <<USAGE
Usage:
  ops/gates/swarm_policy_check.sh \
    --files "file1,file2" \
    [--completed "lint,build,unit"] \
    [--matrix templates/swarm-risk-matrix.yaml] \
    [--mode hard|degraded] \
    [--exception templates/swarm-exception.yaml]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --files)
      FILES_ARG="${2:-}"; shift 2 ;;
    --completed)
      COMPLETED_CHECKS="${2:-}"; shift 2 ;;
    --matrix)
      MATRIX_FILE="${2:-}"; shift 2 ;;
    --mode)
      MODE="${2:-}"; shift 2 ;;
    --exception)
      EXCEPTION_FILE="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2 ;;
  esac
done

if [[ -z "$FILES_ARG" ]]; then
  echo "POLICY_FAIL: --files is required" >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
MATRIX_HELPER="${SWARM_RISK_MATRIX_HELPER:-$ops_home/ops/teamlead/role_opinion_matrix.py}"

if [[ ! -f "$MATRIX_FILE" ]]; then
  echo "POLICY_FAIL: matrix file not found: $MATRIX_FILE" >&2
  exit 1
fi
if [[ ! -f "$MATRIX_HELPER" ]]; then
  echo "POLICY_FAIL: matrix helper not found: $MATRIX_HELPER" >&2
  exit 1
fi

if [[ "$MODE" == "degraded" ]]; then
  if [[ -z "$EXCEPTION_FILE" || ! -f "$EXCEPTION_FILE" ]]; then
    echo "POLICY_FAIL: degraded mode requires --exception <existing-file>" >&2
    exit 1
  fi
  for key in exception_id approved_by expires_utc required_controls; do
    if ! grep -Eq "^[[:space:]]*$key:" "$EXCEPTION_FILE"; then
      echo "POLICY_FAIL: exception file missing key: $key" >&2
      exit 1
    fi
  done
fi

normalize_csv() {
  echo "$1" | tr ',' '\n' | sed 's/^ *//; s/ *$//' | sed '/^$/d' | sort -u
}

join_csv() {
  paste -sd',' -
}

HIGHEST_RISK="$(python3 "$MATRIX_HELPER" --matrix "$MATRIX_FILE" --files "$FILES_ARG" --field highest_risk)"
REQUIRED_CHECKS_CSV="$(python3 "$MATRIX_HELPER" --matrix "$MATRIX_FILE" --files "$FILES_ARG" --field required_checks)"
COMPLETED_NORM="$(normalize_csv "$COMPLETED_CHECKS")"

MISSING=""
if [[ -n "$REQUIRED_CHECKS_CSV" ]]; then
  while IFS= read -r chk; do
    [[ -z "$chk" ]] && continue
    if ! echo "$COMPLETED_NORM" | grep -qx "$chk"; then
      MISSING="$(printf "%s\n%s" "$MISSING" "$chk" | sed '/^$/d')"
    fi
  done < <(echo "$REQUIRED_CHECKS_CSV" | tr ',' '\n')
fi

if [[ -n "$MISSING" ]]; then
  echo "POLICY_FAIL: highest_risk=$HIGHEST_RISK missing_checks=$(echo "$MISSING" | join_csv)" >&2
  exit 1
fi

echo "POLICY_OK: highest_risk=$HIGHEST_RISK required_checks=$REQUIRED_CHECKS_CSV mode=$MODE"
