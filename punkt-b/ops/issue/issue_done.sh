#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/issue/issue_done.sh --issue <id> [--repo owner/repo]

Closes issue only when there are no unpushed commits with `Refs #<id>`,
and performs mandatory lock release by issue id via `lockctl`.
EOF
}

issue_id=""
repo_arg=""

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

repo_root="$(git rev-parse --show-toplevel)"
lock_release_script="$ops_home/ops/issue/lock_release_by_issue.py"
current_branch="$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)"
gates_show_cmd=(gatesctl show-receipt --repo-root "$repo_root")
approval_file="${PUNKTB_PUSH_GATE_APPROVAL_FILE:-}"

if [[ ! -x "$lock_release_script" ]]; then
  echo "[MISSING_LOCK_RELEASE_SCRIPT] expected executable: $lock_release_script" >&2
  exit 2
fi
if [[ "$current_branch" != "dev" ]]; then
  echo "[BRANCH_NOT_DEV] issue:done is dev-only; for prod promotion use npm run release:main -- --issue <release_issue_id>" >&2
  exit 2
fi

validate_issue_done_approval() {
  local file_path="$1"
  local expected_repo_root="$2"
  local expected_branch="$3"
  local expected_issue_id="$4"
  local expected_last_issue_commit="$5"
  python3 - "$file_path" "$expected_repo_root" "$expected_branch" "$expected_issue_id" "$expected_last_issue_commit" <<'PY'
from datetime import datetime, timezone
import json
import re
import sys

file_path, expected_repo_root, expected_branch, expected_issue_id, expected_last_issue_commit = sys.argv[1:6]
try:
    with open(file_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
except FileNotFoundError:
    print("[ISSUE_DONE_APPROVAL_MISSING] approval artifact not found", file=sys.stderr)
    raise SystemExit(1)
except Exception as exc:
    print(f"[ISSUE_DONE_APPROVAL_INVALID] cannot read approval artifact: {exc}", file=sys.stderr)
    raise SystemExit(1)

created_raw = str(payload.get("created_utc", "")).strip()
try:
    created_at = datetime.strptime(created_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
except ValueError:
    print("[ISSUE_DONE_APPROVAL_INVALID] created_utc is missing or malformed", file=sys.stderr)
    raise SystemExit(1)

age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
if age_seconds < 0 or age_seconds > 900:
    print("[ISSUE_DONE_APPROVAL_STALE] approval artifact is older than 15 minutes", file=sys.stderr)
    raise SystemExit(1)

checks = (
    ("repo_root", expected_repo_root),
    ("branch", expected_branch),
    ("issue_id", expected_issue_id),
    ("last_issue_commit", expected_last_issue_commit),
)
for key, expected in checks:
    actual = str(payload.get(key, "")).strip()
    if actual != expected:
        print(f"[ISSUE_DONE_APPROVAL_MISMATCH] {key}={actual!r}, expected {expected!r}", file=sys.stderr)
        raise SystemExit(1)

range_value = str(payload.get("range", "")).strip()
if not range_value:
    print("[ISSUE_DONE_APPROVAL_INVALID] range is missing", file=sys.stderr)
    raise SystemExit(1)

if not re.fullmatch(r"[0-9a-f]{40}", str(payload.get("last_issue_commit", "")).strip()):
    print("[ISSUE_DONE_APPROVAL_INVALID] last_issue_commit is malformed", file=sys.stderr)
    raise SystemExit(1)
PY
}

upstream_ref="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
if [[ -z "$upstream_ref" ]]; then
  echo "[NO_UPSTREAM] current branch has no upstream; push branch first" >&2
  exit 2
fi

refs_pattern="^Refs #${issue_id}$"

unpushed="$(git -C "$repo_root" log --format=%H "${upstream_ref}..HEAD" --grep "$refs_pattern" --extended-regexp --regexp-ignore-case || true)"
if [[ -n "$unpushed" ]]; then
  echo "[UNPUSHED_COMMITS] found local commits with Refs #${issue_id} not pushed to ${upstream_ref}" >&2
  echo "$unpushed" >&2
  exit 2
fi

gh_view_cmd=(gh issue view "$issue_id" --json state,title,number)
if [[ -n "$repo_arg" ]]; then
  gh_view_cmd+=( -R "$repo_arg" )
fi

issue_state="$("${gh_view_cmd[@]}" --jq .state 2>/dev/null || true)"
if [[ -z "$issue_state" ]]; then
  echo "[ISSUE_NOT_FOUND] gh issue view failed for #${issue_id}" >&2
  exit 2
fi

if [[ "$issue_state" != "OPEN" ]]; then
  echo "[ISSUE_NOT_OPEN] issue #${issue_id} state=${issue_state}" >&2
  exit 2
fi

last_sha="$(git -C "$repo_root" log -n 1 --format=%H --grep "$refs_pattern" --extended-regexp --regexp-ignore-case HEAD || true)"
if [[ -z "$last_sha" ]]; then
  echo "[ISSUE_REFS_MISSING] no commit with Refs #${issue_id} found in local history" >&2
  exit 2
fi
receipt_id="n/a"
skip_receipt_check=0
if [[ -n "$approval_file" ]]; then
  if ! validate_issue_done_approval "$approval_file" "$repo_root" "$current_branch" "$issue_id" "$last_sha"; then
    exit 2
  fi
  skip_receipt_check=1
fi

if [[ "$skip_receipt_check" != "1" ]]; then
  if ! receipt_json="$("${gates_show_cmd[@]}" --commit "$last_sha" 2>/dev/null)"; then
    echo "[GATES_RECEIPT_MISSING] no bound gatesctl receipt for last issue commit ${last_sha}" >&2
    exit 2
  fi
  receipt_status="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("status", "")).strip())' <<< "$receipt_json" 2>/dev/null || true)"
  receipt_id="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("receipt_id", "")).strip())' <<< "$receipt_json" 2>/dev/null || true)"
  if [[ "$receipt_status" != "ok" ]]; then
    echo "[GATES_RECEIPT_NOT_OK] receipt ${receipt_id:-n/a} for ${last_sha} has status=${receipt_status:-unknown}" >&2
    exit 2
  fi
fi

if ! lock_release_output="$(python3 "$lock_release_script" --issue-id "$issue_id" --drop-issue --json)"; then
  echo "[LOCK_RELEASE_FAILED] failed to cleanup lock entries for issue #${issue_id}" >&2
  exit 2
fi

lock_cleanup_changed="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("changed") else "0")' <<< "$lock_release_output" 2>/dev/null || echo "0")"
lock_removed_entries="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(payload.get("removed_entries", 0))' <<< "$lock_release_output" 2>/dev/null || echo "0")"
lock_removed_paths="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(len(payload.get("removed_paths", [])))' <<< "$lock_release_output" 2>/dev/null || echo "0")"
comment="Closed by issue:done on branch ${current_branch}"
comment+=" (last commit: ${last_sha}, receipt: ${receipt_id})"

close_cmd=(gh issue close "$issue_id" --comment "$comment")
if [[ -n "$repo_arg" ]]; then
  close_cmd+=( -R "$repo_arg" )
fi

"${close_cmd[@]}" >/dev/null

echo "ISSUE_CLOSED #${issue_id} branch=${current_branch} last_sha=${last_sha:-n/a} receipt=${receipt_id:-n/a} lock_cleanup_changed=${lock_cleanup_changed} lock_removed_entries=${lock_removed_entries} lock_removed_paths=${lock_removed_paths}"
