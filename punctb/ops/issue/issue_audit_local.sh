#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/issue/issue_audit_local.sh [--range <git-range>] [--repo owner/repo] [--skip-gates-audit]

Defaults:
- range: @{upstream}..HEAD when upstream exists, otherwise HEAD
EOF
}

range=""
repo_arg=""
skip_gates_audit=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --range)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --range" >&2; exit 2; }
      range="$2"
      shift 2
      ;;
    --repo)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --repo" >&2; exit 2; }
      repo_arg="$2"
      shift 2
      ;;
    --skip-gates-audit)
      skip_gates_audit=1
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

repo_root="$(git rev-parse --show-toplevel)"
branch_policy="$ops_home/ops/issue/branch_policy_audit.py"
gates_push_script="$ops_home/ops/gates/gates_verify_push.sh"
current_branch="$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)"

if [[ ! -x "$branch_policy" ]]; then
  echo "[MISSING_BRANCH_POLICY] expected executable: $branch_policy" >&2
  exit 2
fi
if [[ ! -x "$gates_push_script" ]]; then
  echo "[MISSING_GATES_PUSH_SCRIPT] expected executable: $gates_push_script" >&2
  exit 2
fi
if [[ "$current_branch" != "dev" ]]; then
  echo "[BRANCH_NOT_DEV] issue:audit:local is dev-only; release flow uses release:main checks" >&2
  exit 2
fi

if [[ -z "$range" ]]; then
  upstream_ref="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
  if [[ -n "$upstream_ref" ]]; then
    range="${upstream_ref}..HEAD"
  else
    range="HEAD"
  fi
fi

cmd=(python3 "$branch_policy" audit-range --target-branch dev --range "$range")
if [[ -n "$repo_arg" ]]; then
  cmd+=(--repo "$repo_arg")
fi

"${cmd[@]}"

if [[ "$skip_gates_audit" != "1" ]]; then
  push_cmd=(bash "$gates_push_script" --target-branch dev --range "$range")
  if [[ -n "$repo_arg" ]]; then
    push_cmd+=(--repo "$repo_arg")
  fi

  "${push_cmd[@]}" >/dev/null
fi
