#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/issue/issue_commit.sh --issue <id> --message "commit subject" --files "path1,path2"
  ops/issue/issue_commit.sh --issue <id> --message "commit subject" --file path1 --file path2

Options:
  --issue <id>         Explicit numeric GitHub issue id.
  --message <text>      Commit message subject/body.
  --files <csv>         Comma-separated file paths.
  --file <path>         Repeatable file path argument.
  --repo <owner/repo>   Optional explicit repo for gh checks.
  --full                Force full pre-push-style gate loop before commit.
  --expand-doc-targets  Allow docs_sync to auto-extend scope with target docs.
EOF
}

issue_id=""
message=""
files_csv=""
repo_arg=""
full_mode=0
expand_doc_targets=0
declare -a files=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --issue" >&2; exit 2; }
      issue_id="$2"
      shift 2
      ;;
    --message)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --message" >&2; exit 2; }
      message="$2"
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
    --full)
      full_mode=1
      shift
      ;;
    --expand-doc-targets)
      expand_doc_targets=1
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
if [[ -z "$message" ]]; then
  echo "[ARGUMENT] --message is required" >&2
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
resolver="$ops_home/ops/issue/lock_issue_resolver.py"
docs_guard="$ops_home/ops/gates/docs_boundary_guard.sh"
branch_policy="$ops_home/ops/issue/branch_policy_audit.py"
lock_release_script="$ops_home/ops/issue/lock_release_by_issue.py"
autoreview_script="$ops_home/ops/gates/autoreview_gate.sh"
docs_sync_script="$ops_home/ops/gates/docs_sync_gate.sh"
dba_review_script="$ops_home/ops/db/dba_review_gate.sh"
teamlead_orchestrator_script="$ops_home/ops/teamlead/teamlead_orchestrator.sh"
gates_verify_commit_script="$ops_home/ops/gates/gates_verify_commit.sh"
gates_bind_commit_script="$ops_home/ops/gates/gates_bind_commit.sh"
matrix_script="$ops_home/ops/teamlead/role_opinion_matrix.py"
matrix_file="$ops_home/templates/swarm-risk-matrix.yaml"
current_branch="$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)"
lockctl_bin="${LOCKCTL_BIN:-lockctl}"
auto_lock_owner="codex:issue-commit-${issue_id}-docs-sync-$$"
auto_lock_lease_sec="${ISSUE_COMMIT_AUTO_LOCK_LEASE_SEC:-1800}"
message_file=""
declare -a auto_acquired_issue_files=()
declare -A docs_sync_targets_map=()
scope_has_process_contract=0
scope_has_migration=0
scope_has_release_main=0
scope_has_major_change=0
scope_has_web=0
scope_has_backend_functions=0
scope_has_ops_runtime=0
docs_sync_mode="advisory"
teamlead_required=0
docs_sync_scope_has_process_contract=0

if [[ ! -x "$resolver" ]]; then
  echo "[MISSING_RESOLVER] expected executable: $resolver" >&2
  exit 2
fi
if [[ ! -x "$docs_guard" ]]; then
  echo "[MISSING_DOCS_GUARD] expected executable: $docs_guard" >&2
  exit 2
fi
if [[ ! -x "$branch_policy" ]]; then
  echo "[MISSING_BRANCH_POLICY] expected executable: $branch_policy" >&2
  exit 2
fi
if [[ ! -x "$lock_release_script" ]]; then
  echo "[MISSING_LOCK_RELEASE_SCRIPT] expected executable: $lock_release_script" >&2
  exit 2
fi
if [[ ! -f "$autoreview_script" ]]; then
  echo "[MISSING_AUTOREVIEW_SCRIPT] expected file: $autoreview_script" >&2
  exit 2
fi
if [[ ! -f "$docs_sync_script" ]]; then
  echo "[MISSING_DOCS_SYNC_SCRIPT] expected file: $docs_sync_script" >&2
  exit 2
fi
if [[ ! -f "$dba_review_script" ]]; then
  echo "[MISSING_DBA_REVIEW_SCRIPT] expected file: $dba_review_script" >&2
  exit 2
fi
if [[ ! -f "$teamlead_orchestrator_script" ]]; then
  echo "[MISSING_TEAMLEAD_ORCHESTRATOR_SCRIPT] expected file: $teamlead_orchestrator_script" >&2
  exit 2
fi
if [[ ! -x "$gates_verify_commit_script" ]]; then
  echo "[MISSING_GATES_VERIFY_COMMIT_SCRIPT] expected executable: $gates_verify_commit_script" >&2
  exit 2
fi
if [[ ! -x "$gates_bind_commit_script" ]]; then
  echo "[MISSING_GATES_BIND_COMMIT_SCRIPT] expected executable: $gates_bind_commit_script" >&2
  exit 2
fi
if [[ ! -f "$matrix_script" ]]; then
  echo "[MISSING_MATRIX_SCRIPT] expected file: $matrix_script" >&2
  exit 2
fi
if [[ ! -f "$matrix_file" ]]; then
  echo "[MISSING_MATRIX_FILE] expected file: $matrix_file" >&2
  exit 2
fi
if [[ "$current_branch" != "dev" ]]; then
  echo "[BRANCH_NOT_DEV] issue-bound commits are allowed only on dev; use release:prepare/release:main for prod flow" >&2
  exit 2
fi

# Remove duplicates while preserving order.
declare -A seen=()
declare -a unique_files=()
for file in "${files[@]}"; do
  if [[ -n "${seen[$file]:-}" ]]; then
    continue
  fi
  seen[$file]=1
  unique_files+=("$file")
done

rebuild_unique_files() {
  declare -A local_seen=()
  declare -a rebuilt=()
  for file in "${unique_files[@]}"; do
    [[ -n "$file" ]] || continue
    if [[ -n "${local_seen[$file]:-}" ]]; then
      continue
    fi
    local_seen[$file]=1
    rebuilt+=("$file")
  done
  unique_files=("${rebuilt[@]}")
}

is_process_contract_file() {
  case "$1" in
    package.json|README.md|AGENTS.md|GEMINI.md|.gitignore|openspec/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

collect_docs_sync_targets() {
  declare -gA docs_sync_targets_map=()
  docs_sync_scope_has_process_contract=0

  local path
  for path in "${unique_files[@]}"; do
    if is_process_contract_file "$path"; then
      docs_sync_scope_has_process_contract=1
      docs_sync_targets_map["README.md"]=1
    fi
    case "$path" in
      web/*)
        docs_sync_targets_map["web/README.md"]=1
        ;;
      backend/*)
        docs_sync_targets_map["backend/README.md"]=1
        ;;
    esac
  done
}

refresh_scope_contract_state() {
  scope_has_process_contract=0
  scope_has_migration=0
  scope_has_release_main=0
  scope_has_major_change=0
  scope_has_web=0
  scope_has_backend_functions=0
  scope_has_ops_runtime=0
  teamlead_required=0
  docs_sync_mode="advisory"

  collect_docs_sync_targets
  scope_has_process_contract="$docs_sync_scope_has_process_contract"

  local file
  for file in "${unique_files[@]}"; do
    if [[ "$file" == web/* ]]; then
      scope_has_web=1
    fi
    if [[ "$file" == backend/functions/* ]]; then
      scope_has_backend_functions=1
    fi
    if [[ "$file" == ops/* || "$file" == git-hooks/* || "$file" == bin/* || "$file" == templates/* ]]; then
      scope_has_ops_runtime=1
    fi
    if [[ "$file" == backend/init/migrations/* || "$file" == backend/init/migration_manifest.lock ]]; then
      scope_has_migration=1
    fi
    if [[ "$file" == "docs/release.md" ]]; then
      scope_has_release_main=1
    fi
  done

  if [[ "$full_mode" == "1" ]]; then
    docs_sync_mode="blocking"
  fi
  if [[ "${PUNCTB_DOCS_SYNC_MODE:-auto}" != "auto" ]]; then
    docs_sync_mode="${PUNCTB_DOCS_SYNC_MODE}"
  fi
  if [[ "$docs_sync_mode" != "blocking" && "$docs_sync_mode" != "advisory" ]]; then
    echo "[INVALID_DOCS_SYNC_MODE] expected blocking|advisory, got: ${docs_sync_mode}" >&2
    exit 2
  fi

  local files_csv_joined matrix_json
  files_csv_joined="$(printf '%s\n' "${unique_files[@]}" | paste -sd',' -)"
  if [[ -n "$files_csv_joined" ]]; then
    matrix_json="$(python3 "$matrix_script" --matrix "$matrix_file" --files "$files_csv_joined")"
    scope_has_major_change="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("major_change") else "0")' <<< "$matrix_json" 2>/dev/null || echo "0")"
  fi

  if [[ "$scope_has_migration" == "1" && "$full_mode" != "1" ]]; then
    echo "[FULL_MODE_REQUIRED] migration scope requires issue:commit --full or migration:apply:guarded" >&2
    exit 2
  fi
  if [[ "$scope_has_release_main" == "1" && "$full_mode" != "1" ]]; then
    echo "[FULL_MODE_REQUIRED] docs/release.md commits require issue:commit --full or release:prepare" >&2
    exit 2
  fi

  if [[ "$full_mode" == "1" && ( "$scope_has_major_change" == "1" || "$scope_has_migration" == "1" || "$scope_has_release_main" == "1" || "${PUNCTB_FORCE_TEAMLEAD:-NO}" == "YES" ) ]]; then
    teamlead_required=1
  fi
}

release_auto_acquired_issue_files() {
  local file
  for file in "${auto_acquired_issue_files[@]}"; do
    "$lockctl_bin" release-path --repo-root "$repo_root" --path "$file" --owner "$auto_lock_owner" >/dev/null 2>&1 || true
  done
  auto_acquired_issue_files=()
}

cleanup() {
  local exit_code=$?
  trap - EXIT
  [[ -n "$message_file" ]] && rm -f "$message_file"
  release_auto_acquired_issue_files
  exit "$exit_code"
}
trap cleanup EXIT

file_in_unique_scope() {
  local target="$1"
  local file
  for file in "${unique_files[@]}"; do
    [[ "$file" == "$target" ]] && return 0
  done
  return 1
}

ensure_docs_sync_target_locks() {
  collect_docs_sync_targets

  if [[ "${#docs_sync_targets_map[@]}" -eq 0 ]]; then
    return 0
  fi

  local file assert_json assert_state acquire_json acquire_ok
  for file in "${!docs_sync_targets_map[@]}"; do
    [[ -f "$file" ]] || continue
    file_in_unique_scope "$file" && continue

    assert_json="$("$resolver" assert-issue-files --issue-id "$issue_id" --files "$file" --json 2>/dev/null || true)"
    assert_state="$(
      JSON_PAYLOAD="$assert_json" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ.get("JSON_PAYLOAD") or "{}")
if payload.get("ok"):
    print("ok")
    raise SystemExit(0)
errors = payload.get("errors", [])
codes = [str(item.get("code", "")) for item in errors if isinstance(item, dict)]
if codes and all(code in {"NO_LOCK", "LOCK_EXPIRED"} for code in codes):
    print("acquire")
else:
    print("blocked")
PY
    )"
    if [[ "$assert_state" == "ok" ]]; then
      continue
    fi
    if [[ "$assert_state" != "acquire" ]]; then
      echo "[DOCS_SYNC_LOCK_CONFLICT] cannot pre-lock ${file} for docs sync in issue #${issue_id}" >&2
      [[ -n "$assert_json" ]] && echo "$assert_json" >&2
      exit 2
    fi

    acquire_json="$("$lockctl_bin" acquire --repo-root "$repo_root" --path "$file" --owner "$auto_lock_owner" --issue "$issue_id" --lease-sec "$auto_lock_lease_sec" 2>&1)" || {
      echo "[DOCS_SYNC_LOCK_ACQUIRE_FAILED] cannot acquire temporary lock for ${file}" >&2
      [[ -n "$acquire_json" ]] && echo "$acquire_json" >&2
      exit 2
    }
    acquire_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$acquire_json" 2>/dev/null || echo "0")"
    if [[ "$acquire_ok" != "1" ]]; then
      echo "[DOCS_SYNC_LOCK_ACQUIRE_FAILED] lockctl acquire returned invalid payload for ${file}" >&2
      [[ -n "$acquire_json" ]] && echo "$acquire_json" >&2
      exit 2
    fi
    auto_acquired_issue_files+=("$file")
  done
}

approve_gate() {
  local gate_name="$1"
  local role_name="$2"
  local evidence_ref="${3:-}"
  local approve_cmd=(gatesctl approve --repo-root "$repo_root" --issue "$issue_id" --gate "$gate_name" --decision approve --actor gatesctl --role "$role_name")
  if [[ -n "$repo_arg" ]]; then
    approve_cmd+=(--repo "$repo_arg")
  fi
  if [[ -n "$evidence_ref" ]]; then
    approve_cmd+=(--evidence-ref "$evidence_ref")
  fi
  approve_cmd+=(--files)
  for file in "${unique_files[@]}"; do
    approve_cmd+=("$file")
  done
  "${approve_cmd[@]}" >/dev/null
}

extend_unique_files_from_contract_json() {
  local json_payload="$1"
  local updated_key="$2"
  local allowed_key="$3"
  local gate_name="$4"
  mapfile -t extra_files < <(
    JSON_PAYLOAD="$json_payload" python3 - "$updated_key" "$allowed_key" <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["JSON_PAYLOAD"])
updated = payload.get(sys.argv[1], [])
allowed = payload.get(sys.argv[2], [])
if not isinstance(updated, list) or not isinstance(allowed, list):
    raise SystemExit(2)
allowed_set = {item.strip() for item in allowed if isinstance(item, str) and item.strip()}
bad = [
    item.strip()
    for item in updated
    if isinstance(item, str) and item.strip() and item.strip() not in allowed_set
]
if bad:
    print(json.dumps({"bad": bad}, ensure_ascii=False))
    raise SystemExit(3)
for item in updated:
    if isinstance(item, str) and item.strip():
        print(item.strip())
PY
  )
  local status=$?
  if [[ "$status" -eq 3 ]]; then
    echo "[${gate_name}_SCOPE_VIOLATION] updated_files must stay within ${allowed_key}" >&2
    printf '%s\n' "${extra_files[@]}" >&2
    exit 2
  fi
  if [[ "$status" -ne 0 ]]; then
    echo "[${gate_name}_INVALID_JSON] expected list payloads for ${updated_key}/${allowed_key}" >&2
    exit 2
  fi
  if [[ ${#extra_files[@]} -gt 0 ]]; then
    unique_files+=("${extra_files[@]}")
    rebuild_unique_files
  fi
}

assert_issue_files() {
  local -a cmd=("$resolver" assert-issue-files --issue-id "$issue_id" --files)
  for file in "${unique_files[@]}"; do
    cmd+=("$file")
  done
  cmd+=(--check-gh --require-open --json)
  if [[ -n "$repo_arg" ]]; then
    cmd+=(--repo "$repo_arg")
  fi
  if ! assert_output="$("${cmd[@]}")"; then
    if [[ -n "$assert_output" ]]; then
      echo "$assert_output" >&2
    fi
    return 1
  fi
}

# Validate explicit issue and lock conflicts for selected files.
if ! assert_issue_files; then
  exit 2
fi

finish_loop_max="${PUNCTB_FINISH_LOOP_MAX:-2}"
if ! [[ "$finish_loop_max" =~ ^[1-9][0-9]*$ ]]; then
  echo "[INVALID_FINISH_LOOP_MAX] expected positive integer, got: $finish_loop_max" >&2
  exit 2
fi

loop_ok=0
docs_sync_artifact_dir=""
docs_sync_gate_executed=0
for (( finish_loop=1; finish_loop<=finish_loop_max; finish_loop++ )); do
  refresh_scope_contract_state
  docs_sync_gate_executed=0
  if [[ "$docs_sync_mode" == "blocking" ]]; then
    ensure_docs_sync_target_locks
  fi
  docs_sync_cmd=(bash "$docs_sync_script" --issue "$issue_id" --mode "$docs_sync_mode")
  for file in "${unique_files[@]}"; do
    docs_sync_cmd+=(--file "$file")
  done
  if docs_sync_json="$("${docs_sync_cmd[@]}")"; then
    :
  elif [[ "$docs_sync_mode" == "blocking" ]]; then
    echo "[DOCS_SYNC_FAILED] issue-bound commit blocked for issue #${issue_id}" >&2
    exit 2
  else
    echo "[DOCS_SYNC_WARN] advisory docs-sync failed for issue #${issue_id}; continuing without blocking" >&2
    docs_sync_json='{"ok": true, "reason": "ADVISORY_FAILED", "updated_files": [], "doc_targets": [], "artifact_dir": ""}'
  fi
  if [[ "$docs_sync_mode" == "blocking" ]]; then
    if [[ "$expand_doc_targets" == "1" ]]; then
      extend_unique_files_from_contract_json "$docs_sync_json" "updated_files" "doc_targets" "DOCS_SYNC"
    else
      docs_sync_needs_expansion="$(
        JSON_PAYLOAD="$docs_sync_json" python3 - "${unique_files[@]}" <<'PY'
import json
import os
import sys

payload = json.loads(os.environ.get("JSON_PAYLOAD") or "{}")
updated = [item.strip() for item in payload.get("updated_files", []) if isinstance(item, str) and item.strip()]
scope = {item.strip() for item in sys.argv[1:] if item.strip()}
needs = any(item not in scope for item in updated)
print("1" if needs else "0")
PY
      )"
      if [[ "$docs_sync_needs_expansion" == "1" ]]; then
        echo "[DOCS_SYNC_SCOPE_EXPANSION_REQUIRED] docs_sync updated files outside explicit scope; rerun with --expand-doc-targets or commit the recommended docs separately" >&2
        exit 2
      fi
    fi
    if ! assert_issue_files; then
      exit 2
    fi
    docs_sync_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$docs_sync_json" 2>/dev/null || echo "0")"
    if [[ "$docs_sync_ok" != "1" ]]; then
      echo "[DOCS_SYNC_FAILED] issue-bound commit blocked for issue #${issue_id}" >&2
      exit 2
    fi
    docs_sync_gate_executed=1
  fi
  docs_sync_artifact_dir="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("artifact_dir", "")).strip())' <<< "$docs_sync_json" 2>/dev/null || true)"
  refresh_scope_contract_state

  migration_scope=()
  non_migration_scope=()
  for file in "${unique_files[@]}"; do
    if [[ "$file" == backend/init/migrations/* || "$file" == backend/init/migration_manifest.lock ]]; then
      migration_scope+=("$file")
    else
      non_migration_scope+=("$file")
    fi
  done

  if [[ ${#migration_scope[@]} -gt 0 ]]; then
    if ! file_in_unique_scope "backend/init/migration_manifest.lock"; then
      manifest_assert_json="$("$resolver" assert-issue-files --issue-id "$issue_id" --files "backend/init/migration_manifest.lock" --json 2>/dev/null || true)"
      manifest_assert_state="$(
        JSON_PAYLOAD="$manifest_assert_json" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ.get("JSON_PAYLOAD") or "{}")
if payload.get("ok"):
    print("ok")
    raise SystemExit(0)
errors = payload.get("errors", [])
codes = [str(item.get("code", "")) for item in errors if isinstance(item, dict)]
if codes and all(code in {"NO_LOCK", "LOCK_EXPIRED"} for code in codes):
    print("acquire")
else:
    print("blocked")
PY
      )"
      if [[ "$manifest_assert_state" == "acquire" ]]; then
        manifest_acquire_json="$("$lockctl_bin" acquire --repo-root "$repo_root" --path "backend/init/migration_manifest.lock" --owner "$auto_lock_owner" --issue "$issue_id" --lease-sec "$auto_lock_lease_sec" 2>&1)" || {
          echo "[DBA_LOCK_ACQUIRE_FAILED] cannot acquire temporary lock for backend/init/migration_manifest.lock" >&2
          [[ -n "$manifest_acquire_json" ]] && echo "$manifest_acquire_json" >&2
          exit 2
        }
        manifest_acquire_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$manifest_acquire_json" 2>/dev/null || echo "0")"
        if [[ "$manifest_acquire_ok" != "1" ]]; then
          echo "[DBA_LOCK_ACQUIRE_FAILED] lockctl acquire returned invalid payload for backend/init/migration_manifest.lock" >&2
          [[ -n "$manifest_acquire_json" ]] && echo "$manifest_acquire_json" >&2
          exit 2
        fi
        auto_acquired_issue_files+=("backend/init/migration_manifest.lock")
      elif [[ "$manifest_assert_state" != "ok" ]]; then
        echo "[DBA_LOCK_CONFLICT] cannot pre-lock backend/init/migration_manifest.lock for issue #${issue_id}" >&2
        [[ -n "$manifest_assert_json" ]] && echo "$manifest_assert_json" >&2
        exit 2
      fi
    fi

    dba_json="$(
      dba_cmd=(bash "$dba_review_script" --issue "$issue_id")
      for file in "${migration_scope[@]}"; do
        dba_cmd+=(--file "$file")
      done
      "${dba_cmd[@]}"
    )"
    extend_unique_files_from_contract_json "$dba_json" "updated_files" "dba_targets" "DBA_REVIEW"
    if ! assert_issue_files; then
      exit 2
    fi
    dba_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$dba_json" 2>/dev/null || echo "0")"
    if [[ "$dba_ok" != "1" ]]; then
      echo "[DBA_REVIEW_FAILED] issue-bound commit blocked for issue #${issue_id}" >&2
      exit 2
    fi
    dba_artifact_dir="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("artifact_dir", "")).strip())' <<< "$dba_json" 2>/dev/null || true)"
    approve_gate "migration-layout-check" "system" "$dba_artifact_dir"
    approve_gate "migration-consistency-check" "system" "$dba_artifact_dir"
    approve_gate "apply-window-approved" "system" "$dba_artifact_dir"

    non_migration_scope=()
    for file in "${unique_files[@]}"; do
      if [[ "$file" != backend/init/migrations/* && "$file" != backend/init/migration_manifest.lock ]]; then
        non_migration_scope+=("$file")
      fi
    done
  fi

  run_autoreview=0
  if [[ "$full_mode" == "1" || "$scope_has_web" == "1" || "$scope_has_backend_functions" == "1" || "$scope_has_ops_runtime" == "1" || "$scope_has_release_main" == "1" ]]; then
    run_autoreview=1
  fi

  if [[ "${PUNCTB_AUTOREVIEW_BYPASS:-NO}" != "YES" && "$run_autoreview" == "1" && ${#non_migration_scope[@]} -gt 0 ]]; then
    autoreview_cmd=(bash "$autoreview_script" --issue "$issue_id")
    for file in "${non_migration_scope[@]}"; do
      autoreview_cmd+=(--file "$file")
    done
    if ! autoreview_json="$("${autoreview_cmd[@]}")"; then
      echo "[AUTOREVIEW_FAILED] issue-bound commit blocked for issue #${issue_id}" >&2
      exit 2
    fi
    autoreview_artifact_dir="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("artifact_dir", "")).strip())' <<< "$autoreview_json" 2>/dev/null || true)"
    approve_gate "autoreview" "system" "$autoreview_artifact_dir"
  elif [[ "${PUNCTB_AUTOREVIEW_BYPASS:-NO}" == "YES" ]]; then
    echo "[AUTOREVIEW_BYPASS] PUNCTB_AUTOREVIEW_BYPASS=YES; skipping autoreview gate for issue #${issue_id}" >&2
  fi

  if [[ "$teamlead_required" != "1" ]]; then
    loop_ok=1
    break
  fi

  teamlead_json="$(
    teamlead_cmd=(bash "$teamlead_orchestrator_script" --issue "$issue_id" --mode milestone)
    for file in "${unique_files[@]}"; do
      teamlead_cmd+=(--file "$file")
    done
    "${teamlead_cmd[@]}"
  )"
  teamlead_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$teamlead_json" 2>/dev/null || echo "0")"
  teamlead_retry="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("retry_required") else "0")' <<< "$teamlead_json" 2>/dev/null || echo "0")"

  if [[ "$teamlead_ok" == "1" ]]; then
    teamlead_artifact_dir="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("artifact_dir", "")).strip())' <<< "$teamlead_json" 2>/dev/null || true)"
    approve_gate "teamlead-orchestration" "system" "$teamlead_artifact_dir"
    approve_gate "specialist-opinions-complete" "system" "$teamlead_artifact_dir"
    auto_commit_eligible="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("auto_commit_eligible") else "0")' <<< "$teamlead_json" 2>/dev/null || echo "0")"
    if [[ "$auto_commit_eligible" == "1" ]]; then
      echo "[GREEN_MILESTONE] issue #${issue_id} scope is auto-commit eligible" >&2
    fi
    loop_ok=1
    break
  fi

  if [[ "$teamlead_retry" == "1" && "$finish_loop" -lt "$finish_loop_max" ]]; then
    continue
  fi

  echo "[TEAMLEAD_FINISH_FAILED] issue-bound commit blocked for issue #${issue_id}" >&2
  exit 2
done

if [[ "$loop_ok" != "1" ]]; then
  echo "[TEAMLEAD_FINISH_EXHAUSTED] finish loop exhausted for issue #${issue_id}" >&2
  exit 2
fi

# Stage only requested paths, including deletions.
git -C "$repo_root" add -A -- "${unique_files[@]}"

if git -C "$repo_root" diff --cached --quiet -- "${unique_files[@]}"; then
  echo "[NO_CHANGES] no staged changes for requested files" >&2
  exit 2
fi

"$docs_guard" --staged --allow-owner-override
approve_gate "lock-scope" "system"
if [[ "$docs_sync_gate_executed" == "1" ]]; then
  approve_gate "docs-sync" "system" "$docs_sync_artifact_dir"
fi
approve_gate "docs-boundary" "system"

policy_cmd=(python3 "$branch_policy" validate-staged --issue-id "$issue_id")
if [[ -n "$repo_arg" ]]; then
  policy_cmd+=(--repo "$repo_arg")
fi
"${policy_cmd[@]}"

tmp_dir="$ops_runtime_root"
mkdir -p "$tmp_dir"
message_file="$(mktemp "$tmp_dir/issue_commit_msg.XXXXXX")"

spawn_agent_id="${SPAWN_AGENT_ID:-unknown}"
spawn_agent_utc="${SPAWN_AGENT_UTC:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
parent_session_id="${PARENT_SESSION_ID:-none}"
{
  printf "# spawn_agent_id: %s\n" "$spawn_agent_id"
  printf "# spawn_agent_utc: %s\n" "$spawn_agent_utc"
  printf "# parent_session_id: %s\n" "$parent_session_id"
  printf "# github_issue: %s\n\n" "$issue_id"
  printf "%s\n" "$message"
} > "$message_file"
"$resolver" ensure-message --message-file "$message_file" --issue-id "$issue_id" >/dev/null

gates_verify_cmd=(bash "$gates_verify_commit_script" --issue "$issue_id" --stage commit)
for file in "${unique_files[@]}"; do
  gates_verify_cmd+=(--file "$file")
done
if [[ -n "$repo_arg" ]]; then
  gates_verify_cmd+=(--repo "$repo_arg")
fi
gates_verify_json="$("${gates_verify_cmd[@]}")"
receipt_ok="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print("1" if payload.get("ok") else "0")' <<< "$gates_verify_json" 2>/dev/null || echo "0")"
if [[ "$receipt_ok" != "1" ]]; then
  echo "[GATES_VERIFY_FAILED] issue-bound commit blocked for issue #${issue_id}" >&2
  exit 2
fi
receipt_id="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("receipt_id", "")).strip())' <<< "$gates_verify_json" 2>/dev/null || true)"
policy_version="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(str(payload.get("policy_version", "")).strip())' <<< "$gates_verify_json" 2>/dev/null || true)"
if [[ -z "$receipt_id" || -z "$policy_version" ]]; then
  echo "[GATES_VERIFY_INVALID] verify did not return receipt_id/policy_version for issue #${issue_id}" >&2
  exit 2
fi
python3 - "$message_file" "$receipt_id" "$policy_version" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
receipt_id = sys.argv[2]
policy_version = sys.argv[3]
text = path.read_text(encoding="utf-8")
lines = text.splitlines()
filtered = [
    line
    for line in lines
    if not re.match(r"^\s*Gate-(Receipt|Policy):", line, flags=re.IGNORECASE)
]
while filtered and filtered[-1] == "":
    filtered.pop()
filtered.extend([
    f"Gate-Receipt: {receipt_id}",
    f"Gate-Policy: {policy_version}",
    "",
])
path.write_text("\n".join(filtered), encoding="utf-8")
PY

git -C "$repo_root" commit --no-verify --cleanup=strip --file "$message_file" --only -- "${unique_files[@]}"

verify_cmd=("$resolver" verify-commit --commit HEAD --check-gh --require-open)
if [[ -n "$repo_arg" ]]; then
  verify_cmd+=(--repo "$repo_arg")
fi
"${verify_cmd[@]}" >/dev/null

bind_status="ok"
bind_cmd=(bash "$gates_bind_commit_script" --issue "$issue_id" --receipt-id "$receipt_id" --commit HEAD)
if [[ -n "$repo_arg" ]]; then
  bind_cmd+=(--repo "$repo_arg")
fi
if ! bind_output="$("${bind_cmd[@]}")"; then
  echo "[GATES_BIND_WARN] failed to bind receipt ${receipt_id} for issue #${issue_id}" >&2
  bind_status="pending"
fi

if [[ "$bind_status" != "ok" ]]; then
  commit_sha="$(git -C "$repo_root" rev-parse --short HEAD)"
  echo "COMMIT_CREATED_BIND_PENDING issue=#${issue_id} sha=${commit_sha} receipt=${receipt_id}" >&2
  exit 2
fi

lock_release_status="ok"
lock_release_removed_paths="0"
lock_release_removed_entries="0"
release_cmd=("$lock_release_script" --issue-id "$issue_id" --files)
for file in "${unique_files[@]}"; do
  release_cmd+=("$file")
done
release_cmd+=(--json)
if ! release_output="$("${release_cmd[@]}")"; then
  lock_release_status="failed"
  echo "[LOCK_RELEASE_WARN] failed to release lock paths for issue #${issue_id}" >&2
elif [[ -n "$release_output" ]]; then
  lock_release_removed_paths="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(len(payload.get("removed_paths", [])))' <<< "$release_output" 2>/dev/null || echo "0")"
  lock_release_removed_entries="$(python3 -c 'import json,sys; payload=json.loads(sys.stdin.read()); print(payload.get("removed_entries", 0))' <<< "$release_output" 2>/dev/null || echo "0")"
fi

commit_sha="$(git -C "$repo_root" rev-parse --short HEAD)"
echo "COMMIT_OK issue=#${issue_id} sha=${commit_sha} receipt=${receipt_id} files=${#unique_files[@]} lock_release=${lock_release_status} removed_paths=${lock_release_removed_paths} removed_entries=${lock_release_removed_entries}"
