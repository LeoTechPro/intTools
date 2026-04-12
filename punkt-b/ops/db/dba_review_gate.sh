#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/db/dba_review_gate.sh --issue <id> --files "path1,path2"
  ops/db/dba_review_gate.sh --issue <id> --file path1 --file path2

Behavior:
- derives migration/manifest scope
- runs migration static checks
- runs dual DBA review with bounded auto-fix loop
- returns JSON summary to stdout
EOF
}

issue_id=""
files_csv=""
max_attempts="${DBA_REVIEW_MAX_ATTEMPTS:-2}"
declare -a files=()

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

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ ${#files[@]} -eq 0 ]]; then
  echo "[ARGUMENT] at least one file must be provided via --files/--file" >&2
  exit 2
fi

declare -A seen=()
declare -a scope_files=()
for file in "${files[@]}"; do
  [[ -n "$file" ]] || continue
  if [[ -n "${seen[$file]:-}" ]]; then
    continue
  fi
  seen["$file"]=1
  scope_files+=("$file")
done

declare -A dba_targets_map=()
for path in "${scope_files[@]}"; do
  case "$path" in
    backend/init/migrations/*)
      dba_targets_map["$path"]=1
      dba_targets_map["backend/init/migration_manifest.lock"]=1
      ;;
    backend/init/migration_manifest.lock)
      dba_targets_map["$path"]=1
      ;;
  esac
done

declare -a dba_targets=()
for path in "${!dba_targets_map[@]}"; do
  if [[ -f "$path" ]]; then
    dba_targets+=("$path")
  fi
done
IFS=$'\n' dba_targets=($(printf '%s\n' "${dba_targets[@]}" | sort))
unset IFS

artifact_dir="${DBA_REVIEW_ARTIFACT_DIR:-$ops_runtime_root/dba-review/${issue_id}/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$artifact_dir"
summary_path="$artifact_dir/summary.json"
scope_file="$artifact_dir/scope-files.txt"
targets_file="$artifact_dir/dba-targets.txt"
printf '%s\n' "${scope_files[@]}" >"$scope_file"
printf '%s\n' "${dba_targets[@]}" >"$targets_file"

schema_file="${DBA_REVIEW_SCHEMA_FILE:-$ops_home/templates/autoreview.schema.json}"
codex_bin="${CODEX_BIN:-$(command -v codex || true)}"
timeout_sec="${CODEX_TIMEOUT_SEC:-240}"

run_with_timeout() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "$timeout_sec" "$@"
  else
    "$@"
  fi
}

hash_snapshot() {
  local out_path="$1"
  shift
  python3 - "$out_path" "$@" <<'PY'
import hashlib
import json
import pathlib
import sys

out_path = pathlib.Path(sys.argv[1])
targets = [pathlib.Path(item) for item in sys.argv[2:]]
payload = {}
for rel in targets:
    if rel.is_file():
        payload[str(rel)] = hashlib.sha256(rel.read_bytes()).hexdigest()
    elif rel.exists():
        payload[str(rel)] = "__non_file__"
    else:
        payload[str(rel)] = "__missing__"
out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

changed_targets_from_snapshots() {
  python3 - "$1" "$2" <<'PY'
import json
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    before = json.load(fh)
with open(sys.argv[2], 'r', encoding='utf-8') as fh:
    after = json.load(fh)
changed = [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]
print("\n".join(changed))
PY
}

dirty_snapshot() {
  local out_path="$1"
  python3 - "$repo_root" "$out_path" <<'PY'
import hashlib
import json
import os
import subprocess
import sys

repo_root, out_path = sys.argv[1:3]
def run(cmd):
    cp = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=True)
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]
paths = sorted(set(
    run(["git", "diff", "--name-only"]) +
    run(["git", "diff", "--cached", "--name-only"]) +
    run(["git", "ls-files", "--others", "--exclude-standard"])
))
snapshot = {}
for rel_path in paths:
    abs_path = os.path.join(repo_root, rel_path)
    if os.path.isfile(abs_path):
        with open(abs_path, "rb") as fh:
            snapshot[rel_path] = hashlib.sha256(fh.read()).hexdigest()
    elif os.path.exists(abs_path):
        snapshot[rel_path] = "__non_file__"
    else:
        snapshot[rel_path] = "__missing__"
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(snapshot, fh, ensure_ascii=False, indent=2, sort_keys=True)
    fh.write("\n")
PY
}

assert_only_targets_changed() {
  local before_path="$1"
  local after_path="$2"
  local allow_file="$3"
  python3 - "$before_path" "$after_path" "$allow_file" <<'PY'
import json
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    before = json.load(fh)
with open(sys.argv[2], 'r', encoding='utf-8') as fh:
    after = json.load(fh)
with open(sys.argv[3], 'r', encoding='utf-8') as fh:
    allowed = {line.strip() for line in fh if line.strip()}
bad = []
for path in sorted(set(before) | set(after)):
    if path in allowed:
        continue
    if before.get(path) != after.get(path):
        bad.append(path)
if bad:
    print("\n".join(bad))
    sys.exit(1)
PY
}

review_verdict() {
  python3 - "$1" <<'PY'
import json
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    payload = json.load(fh)
verdict = payload.get("verdict", "blocked")
summary = payload.get("summary", "")
findings = payload.get("findings", [])
if verdict not in {"ok", "request_changes", "blocked"}:
    print("blocked")
    raise SystemExit(0)
if not isinstance(summary, str) or not summary.strip():
    print("blocked")
    raise SystemExit(0)
if not isinstance(findings, list):
    print("blocked")
    raise SystemExit(0)
if verdict == "ok" and findings:
    print("blocked")
    raise SystemExit(0)
if verdict == "request_changes" and not findings:
    print("blocked")
    raise SystemExit(0)
print(verdict)
PY
}

run_static_checks() {
  local attempt="$1"
  local fail=0
  if ! bash "$ops_home/ops/db/check_migration_layout.sh" >"$artifact_dir/layout_attempt_${attempt}.log" 2>&1; then
    fail=1
  fi
  if ! bash "$ops_home/ops/db/check_migrations_consistency.sh" >"$artifact_dir/consistency_attempt_${attempt}.log" 2>&1; then
    if ! rg -n "required table not found|database connectivity check failed|migration manifest not found|migrations dir not found" "$artifact_dir/consistency_attempt_${attempt}.log" >/dev/null 2>&1; then
      fail=1
    fi
  fi
  return "$fail"
}

if [[ ${#dba_targets[@]} -eq 0 ]]; then
  python3 - "$summary_path" "$issue_id" "$scope_file" "$targets_file" <<'PY'
import json
import sys

summary_path, issue_id, scope_file, targets_file = sys.argv[1:5]
with open(scope_file, 'r', encoding='utf-8') as fh:
    scope = [line.strip() for line in fh if line.strip()]
with open(targets_file, 'r', encoding='utf-8') as fh:
    targets = [line.strip() for line in fh if line.strip()]
payload = {
    "issue_id": int(issue_id),
    "ok": True,
    "reason": "SKIPPED",
    "updated_files": [],
    "scope_files": scope,
    "dba_targets": targets,
    "artifact_dir": str(summary_path.rsplit("/", 1)[0]),
}
with open(summary_path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(json.dumps(payload, ensure_ascii=False))
PY
  exit 0
fi

if [[ -z "$codex_bin" || ! -x "$codex_bin" ]]; then
  echo "[CODEX_MISSING] codex CLI is required for dba review gate" >&2
  exit 2
fi

initial_snapshot="$artifact_dir/targets_initial.json"
hash_snapshot "$initial_snapshot" "${dba_targets[@]}"

attempt=1
final_reason="MAX_ATTEMPTS_EXCEEDED"
while [[ "$attempt" -le "$max_attempts" ]]; do
  if ! run_static_checks "$attempt"; then
    final_reason="STATIC_CHECK_FAILED"
    break
  fi

  reviewer_a_json="$artifact_dir/reviewer_a_attempt_${attempt}.json"
  reviewer_b_json="$artifact_dir/reviewer_b_attempt_${attempt}.json"
  reviewer_a_log="$artifact_dir/reviewer_a_attempt_${attempt}.log"
  reviewer_b_log="$artifact_dir/reviewer_b_attempt_${attempt}.log"

  reviewer_prompt_base="$(cat <<EOF
Ты выполняешь DBA-review для issue #$issue_id.

Migration scope:
$(sed 's/^/- /' "$targets_file")

Правила:
- Работай только в read-only режиме.
- Проверяй миграции, manifest sync, rollback safety, idempotency expectations, schema_migrations contract, layout and obvious RLS/ACL risks.
- verdict=ok только если замечаний нет.
- verdict=request_changes только если правки реально нужны внутри migration scope.
- verdict=blocked если корректная оценка невозможна без внешнего решения/данных.
EOF
)"

  if ! run_with_timeout "$codex_bin" exec --sandbox read-only --ephemeral --output-schema "$schema_file" --output-last-message "$reviewer_a_json" "Ты reviewer A. $reviewer_prompt_base" >"$reviewer_a_log" 2>&1; then
    final_reason="REVIEWER_A_FAILED"
    break
  fi
  verdict_a="$(review_verdict "$reviewer_a_json")"
  if [[ "$verdict_a" == "request_changes" ]]; then
    before_dirty="$artifact_dir/fixer_a_before_${attempt}.json"
    after_dirty="$artifact_dir/fixer_a_after_${attempt}.json"
    fixer_log="$artifact_dir/fixer_a_attempt_${attempt}.log"
    fixer_text="$artifact_dir/fixer_a_attempt_${attempt}.txt"
    dirty_snapshot "$before_dirty"
    fixer_prompt="$(cat <<EOF
Исправь замечания DBA reviewer A для issue #$issue_id.

Разрешённый scope:
$(sed 's/^/- /' "$targets_file")

Ограничения:
- Можно менять только перечисленные файлы.
- Нельзя делать commit/push или запускать миграции.

Отчёт reviewer:
$(cat "$reviewer_a_json")
EOF
)"
    if ! run_with_timeout "$codex_bin" exec --sandbox workspace-write --ephemeral --output-last-message "$fixer_text" "$fixer_prompt" >"$fixer_log" 2>&1; then
      final_reason="FIXER_AFTER_A_FAILED"
      break
    fi
    dirty_snapshot "$after_dirty"
    if ! assert_only_targets_changed "$before_dirty" "$after_dirty" "$targets_file" >/dev/null; then
      final_reason="SCOPE_VIOLATION"
      break
    fi
    attempt=$((attempt + 1))
    continue
  fi
  if [[ "$verdict_a" != "ok" ]]; then
    final_reason="REVIEWER_A_BLOCKED"
    break
  fi

  if ! run_with_timeout "$codex_bin" exec --sandbox read-only --ephemeral --output-schema "$schema_file" --output-last-message "$reviewer_b_json" "Ты reviewer B. Игнорируй вывод reviewer A и независимо выполни DBA-review. $reviewer_prompt_base" >"$reviewer_b_log" 2>&1; then
    final_reason="REVIEWER_B_FAILED"
    break
  fi
  verdict_b="$(review_verdict "$reviewer_b_json")"
  if [[ "$verdict_b" == "request_changes" ]]; then
    before_dirty="$artifact_dir/fixer_b_before_${attempt}.json"
    after_dirty="$artifact_dir/fixer_b_after_${attempt}.json"
    fixer_log="$artifact_dir/fixer_b_attempt_${attempt}.log"
    fixer_text="$artifact_dir/fixer_b_attempt_${attempt}.txt"
    dirty_snapshot "$before_dirty"
    fixer_prompt="$(cat <<EOF
Исправь замечания DBA reviewer B для issue #$issue_id.

Разрешённый scope:
$(sed 's/^/- /' "$targets_file")

Ограничения:
- Можно менять только перечисленные файлы.
- Нельзя делать commit/push или запускать миграции.

Отчёт reviewer:
$(cat "$reviewer_b_json")
EOF
)"
    if ! run_with_timeout "$codex_bin" exec --sandbox workspace-write --ephemeral --output-last-message "$fixer_text" "$fixer_prompt" >"$fixer_log" 2>&1; then
      final_reason="FIXER_AFTER_B_FAILED"
      break
    fi
    dirty_snapshot "$after_dirty"
    if ! assert_only_targets_changed "$before_dirty" "$after_dirty" "$targets_file" >/dev/null; then
      final_reason="SCOPE_VIOLATION"
      break
    fi
    attempt=$((attempt + 1))
    continue
  fi
  if [[ "$verdict_b" != "ok" ]]; then
    final_reason="REVIEWER_B_BLOCKED"
    break
  fi

  final_reason="OK"
  break
done

final_snapshot="$artifact_dir/targets_final.json"
hash_snapshot "$final_snapshot" "${dba_targets[@]}"
mapfile -t changed_targets < <(changed_targets_from_snapshots "$initial_snapshot" "$final_snapshot")

python3 - "$summary_path" "$issue_id" "$scope_file" "$targets_file" "$artifact_dir" "$final_reason" "${changed_targets[@]}" <<'PY'
import json
import sys

summary_path, issue_id, scope_file, targets_file, artifact_dir, reason, *changed = sys.argv[1:]
with open(scope_file, 'r', encoding='utf-8') as fh:
    scope = [line.strip() for line in fh if line.strip()]
with open(targets_file, 'r', encoding='utf-8') as fh:
    targets = [line.strip() for line in fh if line.strip()]
payload = {
    "issue_id": int(issue_id),
    "ok": reason == "OK" or reason == "SKIPPED",
    "reason": reason,
    "updated_files": [item for item in changed if item.strip()],
    "scope_files": scope,
    "dba_targets": targets,
    "artifact_dir": artifact_dir,
}
with open(summary_path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(json.dumps(payload, ensure_ascii=False))
PY

[[ "$final_reason" == "OK" ]]
