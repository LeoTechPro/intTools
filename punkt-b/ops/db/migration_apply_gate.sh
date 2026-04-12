#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/db/migration_apply_gate.sh --issue <id> --files "path1,path2"
  ops/db/migration_apply_gate.sh --issue <id> --file path1 --file path2
  ops/db/migration_apply_gate.sh --issue <id> --files "..." -- <migration command...>

Behavior:
- validates issue-bound migration scope
- runs dual DBA gate before any apply command
- executes the guarded migration command only after DBA_REVIEW_OK
EOF
}

issue_id=""
files_csv=""
repo_arg=""
declare -a files=()
declare -a apply_cmd=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --issue" >&2; exit 2; }
      issue_id="$2"
      shift 2
      ;;
    --files)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --files" >&2; exit 2; }
      files_csv="$2"
      shift 2
      ;;
    --file)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --file" >&2; exit 2; }
      files+=("$2")
      shift 2
      ;;
    --repo)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --repo" >&2; exit 2; }
      repo_arg="$2"
      shift 2
      ;;
    --)
      shift
      apply_cmd=("$@")
      break
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
if ! [[ "$issue_id" =~ ^[1-9][0-9]*$ ]]; then
  echo "[INVALID_ISSUE_ID] expected numeric issue id, got: $issue_id" >&2
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

if [[ ${#apply_cmd[@]} -eq 0 ]]; then
  apply_cmd=(bash backend/init/010_supabase_migrate.sh)
fi

repo_root="$(git rev-parse --show-toplevel)"
resolver="$ops_home/ops/issue/lock_issue_resolver.py"
dba_review_script="$ops_home/ops/db/dba_review_gate.sh"
cd "$repo_root"

if [[ ! -x "$resolver" ]]; then
  echo "[MISSING_RESOLVER] expected executable: $resolver" >&2
  exit 2
fi
if [[ ! -f "$dba_review_script" ]]; then
  echo "[MISSING_DBA_REVIEW_SCRIPT] expected file: $dba_review_script" >&2
  exit 2
fi

declare -A seen=()
declare -a migration_scope=()
for file in "${files[@]}"; do
  [[ -n "$file" ]] || continue
  if [[ -n "${seen[$file]:-}" ]]; then
    continue
  fi
  seen[$file]=1
  case "$file" in
    backend/init/migrations/*|backend/init/migration_manifest.lock)
      migration_scope+=("$file")
      ;;
    *)
      echo "[NON_MIGRATION_SCOPE] only backend/init/migrations/* and backend/init/migration_manifest.lock are allowed: $file" >&2
      exit 2
      ;;
  esac
done

if [[ -f "$repo_root/backend/init/migration_manifest.lock" ]]; then
  manifest_seen=0
  for file in "${migration_scope[@]}"; do
    if [[ "$file" == "backend/init/migration_manifest.lock" ]]; then
      manifest_seen=1
      break
    fi
  done
  if [[ "$manifest_seen" != "1" ]]; then
    migration_scope+=("backend/init/migration_manifest.lock")
  fi
fi

assert_cmd=("$resolver" assert-issue-files --issue-id "$issue_id" --files)
for file in "${migration_scope[@]}"; do
  assert_cmd+=("$file")
done
assert_cmd+=(--check-gh --require-open --json)
if [[ -n "$repo_arg" ]]; then
  assert_cmd+=(--repo "$repo_arg")
fi
if ! assert_output="$("${assert_cmd[@]}")"; then
  if [[ -n "$assert_output" ]]; then
    echo "$assert_output" >&2
  fi
  exit 2
fi

dba_cmd=(bash "$dba_review_script" --issue "$issue_id")
for file in "${migration_scope[@]}"; do
  dba_cmd+=(--file "$file")
done
dba_json="$("${dba_cmd[@]}")"
dba_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$dba_json" 2>/dev/null || echo "0")"
if [[ "$dba_ok" != "1" ]]; then
  echo "[DBA_REVIEW_FAILED] guarded migration apply blocked for issue #${issue_id}" >&2
  exit 2
fi

"${apply_cmd[@]}"
echo "MIGRATION_APPLY_OK issue=#${issue_id} scope_files=${#migration_scope[@]}"
