#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/gates/gates_verify_push.sh [--target-branch dev|main] --range <git-range> [--repo owner/repo]
EOF
}

target_branch=""
range_arg=""
repo_arg=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-branch)
      target_branch="$2"
      shift 2
      ;;
    --range)
      range_arg="$2"
      shift 2
      ;;
    --repo)
      repo_arg="$2"
      shift 2
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

if [[ -z "$range_arg" ]]; then
  echo "[ARGUMENT] --range is required" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
if [[ -z "$target_branch" ]]; then
  target_branch="$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)"
fi
if [[ "$target_branch" != "dev" && "$target_branch" != "main" ]]; then
  echo "[ARGUMENT] --target-branch must be dev or main; got: $target_branch" >&2
  exit 2
fi
cmd=(gatesctl audit-range --repo-root "$repo_root" --target-branch "$target_branch" --range "$range_arg" --format json)
if [[ -n "$repo_arg" ]]; then
  cmd+=(--repo "$repo_arg")
fi

"${cmd[@]}"
