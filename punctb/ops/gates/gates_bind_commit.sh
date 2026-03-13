#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/gates/gates_bind_commit.sh [--issue <id>] [--receipt-id <id>|--receipt <id>] [--commit <sha>] [--repo owner/repo] [--post-issue]
EOF
}

issue_id=""
receipt_id=""
commit_sha="HEAD"
repo_arg=""
post_issue=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      issue_id="$2"
      shift 2
      ;;
    --receipt-id)
      receipt_id="$2"
      shift 2
      ;;
    --receipt)
      receipt_id="$2"
      shift 2
      ;;
    --commit)
      commit_sha="$2"
      shift 2
      ;;
    --repo)
      repo_arg="$2"
      shift 2
      ;;
    --post-issue)
      post_issue=1
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
cmd=(gatesctl bind-commit --repo-root "$repo_root" --commit-sha "$commit_sha" --format json)
if [[ -n "$issue_id" ]]; then
  cmd+=(--issue "$issue_id")
fi
if [[ -n "$receipt_id" ]]; then
  cmd+=(--receipt-id "$receipt_id")
fi
if [[ -n "$repo_arg" ]]; then
  cmd+=(--repo "$repo_arg")
fi
if [[ "$post_issue" -eq 1 ]]; then
  cmd+=(--post-issue)
fi

"${cmd[@]}"
