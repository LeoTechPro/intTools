#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/gates/gates_verify_commit.sh --issue <id> [--stage commit] --files "path1,path2"
  ops/gates/gates_verify_commit.sh --issue <id> [--stage commit] --file path1 --file path2
EOF
}

issue_id=""
stage="commit"
repo_arg=""
files_csv=""
declare -a files=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      issue_id="$2"
      shift 2
      ;;
    --stage)
      stage="$2"
      shift 2
      ;;
    --files)
      files_csv="$2"
      shift 2
      ;;
    --file)
      files+=("$2")
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

if [[ -z "$issue_id" ]]; then
  echo "[ARGUMENT] --issue is required" >&2
  exit 2
fi

if [[ -n "$files_csv" ]]; then
  IFS=',' read -r -a csv_parts <<< "$files_csv"
  for part in "${csv_parts[@]}"; do
    part="${part#${part%%[![:space:]]*}}"
    part="${part%${part##*[![:space:]]}}"
    [[ -n "$part" ]] && files+=("$part")
  done
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "[ARGUMENT] at least one file must be provided via --files/--file" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
policy_file="$ops_home/docs/policy/gates.v1.yaml"
cmd=(gatesctl verify --repo-root "$repo_root" --policy-file "$policy_file" --issue "$issue_id" --stage "$stage" --sync-issue --format json)
if [[ -n "$repo_arg" ]]; then
  cmd+=(--repo "$repo_arg")
fi
cmd+=(--files)
for file in "${files[@]}"; do
  cmd+=("$file")
done

"${cmd[@]}"
