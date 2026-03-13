#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/gates/docs_boundary_guard.sh --staged [--allow-owner-override]
  ops/gates/docs_boundary_guard.sh --range <git-range> [--allow-owner-override]

Rules:
- Blocks NEW files in docs/** (status A) unless owner override is enabled.
- Internal ops/process docs live outside the product repo in `$PUNCTB_OPS_HOME/docs/**`.
EOF
}

mode_staged=0
range_arg=""
allow_owner_override=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --staged)
      mode_staged=1
      shift
      ;;
    --range)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --range" >&2; exit 2; }
      range_arg="$2"
      shift 2
      ;;
    --allow-owner-override)
      allow_owner_override=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ARGUMENT] unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$mode_staged" -eq 1 && -n "$range_arg" ]]; then
  echo "[ARGUMENT] use exactly one mode: --staged or --range <git-range>" >&2
  exit 2
fi
if [[ "$mode_staged" -eq 0 && -z "$range_arg" ]]; then
  echo "[ARGUMENT] use exactly one mode: --staged or --range <git-range>" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
declare -a docs_new_violations=()
collect_changes() {
  if [[ "$mode_staged" -eq 1 ]]; then
    git -C "$repo_root" diff --cached --name-status --no-renames -z
  else
    git -C "$repo_root" diff --name-status --no-renames -z "$range_arg"
  fi
}

while IFS= read -r -d '' status && IFS= read -r -d '' path; do
  [[ -z "${status:-}" ]] && continue
  [[ -z "${path:-}" ]] && continue
  status="${status%%$'\t'*}"
  status="${status:0:1}"

  if [[ "$status" == "A" && "$path" == docs/* ]]; then
    docs_new_violations+=("$path")
  fi

done < <(collect_changes)

if [[ "$allow_owner_override" -eq 1 && "${PUNCTB_DOCS_OWNER_APPROVED:-NO}" == "YES" ]]; then
  if [[ ${#docs_new_violations[@]} -gt 0 ]]; then
    echo "[DOCS_BOUNDARY_OVERRIDE] owner override accepted via PUNCTB_DOCS_OWNER_APPROVED=YES"
  fi
  docs_new_violations=()
fi

if [[ ${#docs_new_violations[@]} -eq 0 ]]; then
  exit 0
fi

if [[ ${#docs_new_violations[@]} -gt 0 ]]; then
  echo "[DOCS_BOUNDARY_VIOLATION] creating new files in docs/** is forbidden without owner override" >&2
  for path in "${docs_new_violations[@]}"; do
    echo " - $path" >&2
  done
  echo "For explicit owner exception set PUNCTB_DOCS_OWNER_APPROVED=YES and pass --allow-owner-override." >&2
fi

echo "Internal process docs live in \$PUNCTB_OPS_HOME/docs/**, not in /git/punctb/docs/**." >&2
exit 2
