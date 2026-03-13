#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/issue/issue_push_done.sh --issue <id> [--repo owner/repo] [--skip-acceptance-check] [--allow-no-checklist]

Flow:
1) Audit local range @{upstream}..HEAD
2) Verify issue is OPEN
3) Verify acceptance checklist is complete (unless skipped)
4) git push
5) issue:done
EOF
}

issue_id=""
repo_arg=""
skip_acceptance_check=0
allow_no_checklist=0

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
    --skip-acceptance-check)
      skip_acceptance_check=1
      shift
      ;;
    --allow-no-checklist)
      allow_no_checklist=1
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

if [[ -z "$issue_id" ]]; then
  echo "[ARGUMENT] --issue is required" >&2
  exit 2
fi

if ! [[ "$issue_id" =~ ^[1-9][0-9]*$ ]]; then
  echo "[INVALID_ISSUE_ID] expected numeric issue id, got: $issue_id" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
current_branch="$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)"
teamlead_orchestrator_script="$ops_home/ops/teamlead/teamlead_orchestrator.sh"
gates_show_cmd=(gatesctl show-receipt --repo-root "$repo_root")
if [[ "$current_branch" != "dev" ]]; then
  echo "[BRANCH_NOT_DEV] issue:push:done is dev-only; for prod promotion use npm run release:main -- --issue <release_issue_id>" >&2
  exit 2
fi

upstream_ref="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
if [[ -z "$upstream_ref" ]]; then
  echo "[NO_UPSTREAM] current branch has no upstream; configure upstream first" >&2
  exit 2
fi

if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "[DIRTY_TREE] working tree is not clean; commit or stash changes before push+done" >&2
  exit 2
fi

audit_script="$ops_home/ops/issue/issue_audit_local.sh"
done_script="$ops_home/ops/issue/issue_done.sh"
if [[ ! -x "$audit_script" ]]; then
  echo "[MISSING_AUDIT_SCRIPT] expected executable: $audit_script" >&2
  exit 2
fi
if [[ ! -x "$done_script" ]]; then
  echo "[MISSING_DONE_SCRIPT] expected executable: $done_script" >&2
  exit 2
fi
if [[ ! -f "$teamlead_orchestrator_script" ]]; then
  echo "[MISSING_TEAMLEAD_ORCHESTRATOR_SCRIPT] expected file: $teamlead_orchestrator_script" >&2
  exit 2
fi

audit_range="${upstream_ref}..HEAD"
refs_pattern="^Refs #${issue_id}$"
bash "$audit_script" --range "$audit_range" >/dev/null

mapfile -t range_files < <(git -C "$repo_root" diff --name-only "$audit_range")
if [[ ${#range_files[@]} -gt 0 ]]; then
  finish_cmd=(bash "$teamlead_orchestrator_script" --issue "$issue_id" --mode finish)
  for file in "${range_files[@]}"; do
    [[ -n "$file" ]] && finish_cmd+=(--file "$file")
  done
  finish_json="$("${finish_cmd[@]}")"
  finish_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$finish_json" 2>/dev/null || echo "0")"
  if [[ "$finish_ok" != "1" ]]; then
    echo "[TEAMLEAD_FINISH_FAILED] final finish orchestration blocked push for issue #${issue_id}" >&2
    exit 2
  fi
fi

gh_view_cmd=(gh issue view "$issue_id" --json state,body,number,title)
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

if [[ "$skip_acceptance_check" -eq 0 ]]; then
  issue_body="$("${gh_view_cmd[@]}" --jq .body 2>/dev/null || true)"
  acceptance_block="$(awk '
    BEGIN { in_section=0 }
    /^##[[:space:]]+Acceptance([[:space:]]|$)/ { in_section=1; next }
    /^##[[:space:]]+/ { if (in_section) exit }
    { if (in_section) print }
  ' <<< "$issue_body")"
  checklist_source="$acceptance_block"
  if [[ -z "$checklist_source" ]]; then
    checklist_source="$issue_body"
  fi

  checklist_lines="$(grep -E '^[[:space:]]*[-*][[:space:]]+\[[ xX]\]' <<< "$checklist_source" || true)"
  checklist_total="$(sed '/^[[:space:]]*$/d' <<< "$checklist_lines" | wc -l | tr -d ' ')"
  checklist_unchecked="$(grep -Ec '\[[[:space:]]\]' <<< "$checklist_lines" || true)"

  if [[ "$checklist_total" -eq 0 && "$allow_no_checklist" -eq 0 ]]; then
    echo "[ACCEPTANCE_NOT_FOUND] no acceptance checklist found in issue #${issue_id}" >&2
    echo "Use --allow-no-checklist to bypass this guard explicitly." >&2
    exit 2
  fi

  if [[ "$checklist_unchecked" -gt 0 ]]; then
    echo "[ACCEPTANCE_NOT_DONE] issue #${issue_id} has unchecked acceptance items: ${checklist_unchecked}" >&2
    exit 2
  fi
fi

last_issue_commit="$(git -C "$repo_root" log -n 1 --format=%H "${audit_range}" --grep "$refs_pattern" --extended-regexp --regexp-ignore-case || true)"
if [[ -z "$last_issue_commit" ]]; then
  echo "[GATES_RECEIPT_MISSING] no issue commit with Refs #${issue_id} found in push range ${audit_range}" >&2
  exit 2
fi
if ! receipt_json="$("${gates_show_cmd[@]}" --commit "$last_issue_commit" 2>/dev/null)"; then
  echo "[GATES_RECEIPT_MISSING] no bound gatesctl receipt for ${last_issue_commit}" >&2
  exit 2
fi
receipt_status="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("status", "")).strip())' <<< "$receipt_json" 2>/dev/null || true)"
if [[ "$receipt_status" != "ok" ]]; then
  echo "[GATES_RECEIPT_NOT_OK] receipt for ${last_issue_commit} has status=${receipt_status:-unknown}" >&2
  exit 2
fi

git -C "$repo_root" push

done_cmd=(bash "$done_script" --issue "$issue_id")
if [[ -n "$repo_arg" ]]; then
  done_cmd+=( --repo "$repo_arg" )
fi
"${done_cmd[@]}" >/dev/null

cleanup_targets=(
  "$ops_runtime_root/autoreview/$issue_id"
  "$ops_runtime_root/docs-sync/$issue_id"
  "$ops_runtime_root/dba-review/$issue_id"
  "$ops_runtime_root/teamlead-finish/$issue_id"
  "$ops_runtime_root/teamlead-orchestrator/$issue_id"
  "$ops_runtime_root/opinions/$issue_id"
)
for target in "${cleanup_targets[@]}"; do
  [[ -e "$target" ]] || continue
  rm -rf -- "$target"
done

echo "PUSH_DONE_OK issue=#${issue_id} branch=${current_branch} range=${audit_range}"
