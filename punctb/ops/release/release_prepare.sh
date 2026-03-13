#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/release/release_prepare.sh --issue <release_issue_id> [--repo owner/repo] [--date YYYY-MM-DD]

Flow:
1) verify clean dev worktree
2) rebuild docs/release.md from release issue + included closed release-note issues
3) commit docs/release.md via issue_commit.sh under the same release issue
EOF
}

issue_id=""
repo_arg=""
date_arg=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --issue" >&2; exit 2; }
      issue_id="$2"
      shift 2
      ;;
    --repo)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --repo" >&2; exit 2; }
      repo_arg="$2"
      shift 2
      ;;
    --date)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --date" >&2; exit 2; }
      date_arg="$2"
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

if [[ -z "$issue_id" ]]; then
  echo "[ARGUMENT] --issue is required" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
current_branch="$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "dev" ]]; then
  echo "[BRANCH_NOT_DEV] release:prepare must run on dev" >&2
  exit 2
fi

if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "[DIRTY_TREE] working tree is not clean; release:prepare requires a clean tree" >&2
  exit 2
fi

prepare_cmd=(python3 "$ops_home/ops/release/release_prepare.py" --issue "$issue_id")
if [[ -n "$repo_arg" ]]; then
  prepare_cmd+=(--repo "$repo_arg")
fi
if [[ -n "$date_arg" ]]; then
  prepare_cmd+=(--date "$date_arg")
fi
"${prepare_cmd[@]}"

if git -C "$repo_root" diff --quiet -- docs/release.md; then
  echo "RELEASE_PREPARE_OK issue=#${issue_id} changed=0"
  exit 0
fi

commit_cmd=(bash "$ops_home/ops/issue/issue_commit.sh" --issue "$issue_id" --message "docs(release): подготовить релизную запись" --file "docs/release.md")
if [[ -n "$repo_arg" ]]; then
  commit_cmd+=(--repo "$repo_arg")
fi
"${commit_cmd[@]}"

echo "RELEASE_PREPARE_OK issue=#${issue_id} changed=1"
