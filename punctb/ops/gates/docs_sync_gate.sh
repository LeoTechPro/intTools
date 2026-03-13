#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/gates/docs_sync_gate.sh --issue <id> --files "path1,path2"
  ops/gates/docs_sync_gate.sh --issue <id> --file path1 --file path2
  ops/gates/docs_sync_gate.sh --issue <id> --mode auto|blocking|advisory --files "path1,path2"

Behavior:
- derives internal documentation targets from changed code/process files
- updates only existing non-user-facing docs/README files
- runs a docs review gate and returns JSON summary to stdout
EOF
}

issue_id=""
files_csv=""
mode="auto"
max_attempts="${DOCS_SYNC_MAX_ATTEMPTS:-2}"
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
    --mode)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --mode" >&2; exit 2; }
      mode="$2"
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
if [[ "$mode" != "auto" && "$mode" != "blocking" && "$mode" != "advisory" ]]; then
  echo "[INVALID_MODE] expected auto|blocking|advisory, got: $mode" >&2
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

declare -A docs_targets_map=()
scope_has_process_contract=0
declare -A scope_map=()
for path in "${scope_files[@]}"; do
  scope_map["$path"]=1
  case "$path" in
    package.json|README.md|AGENTS.md|GEMINI.md|.gitignore|openspec/*)
      scope_has_process_contract=1
      docs_targets_map["README.md"]=1
      ;;
    web/*)
      docs_targets_map["web/README.md"]=1
      ;;
    backend/*)
      docs_targets_map["backend/README.md"]=1
      ;;
  esac
done

declare -a doc_targets=()
for path in "${!docs_targets_map[@]}"; do
  if [[ -f "$path" ]]; then
    doc_targets+=("$path")
  fi
done
IFS=$'\n' doc_targets=($(printf '%s\n' "${doc_targets[@]}" | sort))
unset IFS

doc_targets_already_in_scope=1
for path in "${doc_targets[@]}"; do
  if [[ -z "${scope_map[$path]:-}" ]]; then
    doc_targets_already_in_scope=0
    break
  fi
done

effective_mode="$mode"
if [[ "$effective_mode" == "auto" ]]; then
  if [[ "$scope_has_process_contract" -eq 1 ]]; then
    effective_mode="blocking"
  else
    effective_mode="advisory"
  fi
fi

artifact_dir="${DOCS_SYNC_ARTIFACT_DIR:-$ops_runtime_root/docs-sync/${issue_id}/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$artifact_dir"

summary_path="$artifact_dir/summary.json"
scope_file="$artifact_dir/scope-files.txt"
targets_file="$artifact_dir/doc-targets.txt"
printf '%s\n' "${scope_files[@]}" >"$scope_file"
printf '%s\n' "${doc_targets[@]}" >"$targets_file"

schema_file="${DOCS_SYNC_SCHEMA_FILE:-$ops_home/templates/autoreview.schema.json}"
codex_bin="${CODEX_BIN:-$(command -v codex || true)}"
timeout_sec="${CODEX_TIMEOUT_SEC:-180}"

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

render_prompt_context() {
  python3 - "$@" <<'PY'
import pathlib
import sys

def split_sections(lines):
    sections = []
    current_heading = None
    current_lines = []
    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = line
            current_lines = [line]
            continue
        if current_heading is None:
            current_lines.append(line)
        else:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, current_lines))
    elif current_lines:
        sections.append(("", current_lines))
    return sections


def pick_relevant(raw, text):
    lines = text.splitlines()
    sections = split_sections(lines)
    if raw == "README.md":
        wanted = {
            "## Git Issue Workflow (issue-id driven commit path)",
        }
    elif raw.endswith("issue-commit-flow.md"):
        wanted = {
            "## Назначение",
            "## Компоненты",
            "## Алгоритм `issue_commit --issue`",
            "## Алгоритм `migration_apply_gate --issue`",
            "## Алгоритм `autoreview_gate --issue`",
            "## Алгоритм `teamlead_orchestrator`",
            "## Алгоритм `issue_done --issue`",
            "## Базовый рабочий цикл",
            "## Finish: local vs remote",
        }
    elif raw.endswith("scripts.md"):
        wanted = {
            "## issue_commit.sh",
            "## docs_sync_gate.sh",
            "## teamlead_orchestrator.sh",
            "## role_opinion_matrix.py",
            "## migration_apply_gate.sh",
            "## lock_release_by_issue.py",
            "## issue_done.sh",
            "## issue_push_done.sh",
            "## branch_policy_audit.py",
        }
    else:
        return text[:12000]

    picked = []
    for heading, content in sections:
        if heading in wanted:
            picked.append("\n".join(content).rstrip())
    if not picked:
        return text[:12000]
    return "\n\n".join(picked)


for raw in sys.argv[1:]:
    path = pathlib.Path(raw)
    print(f"===== {raw} =====")
    if not path.exists():
        print("<missing>")
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("<binary>")
        continue
    excerpt = pick_relevant(raw, text)
    print(excerpt.rstrip())
    print()
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

emit_summary() {
  local reason="$1"
  local ok_flag="$2"
  python3 - "$summary_path" "$issue_id" "$scope_file" "$targets_file" "$artifact_dir" "$reason" "$ok_flag" "$effective_mode" "$scope_has_process_contract" <<'PY'
import json
import sys

summary_path, issue_id, scope_file, targets_file, artifact_dir, reason, ok_flag, mode, process_scope = sys.argv[1:10]
with open(scope_file, 'r', encoding='utf-8') as fh:
    scope = [line.strip() for line in fh if line.strip()]
with open(targets_file, 'r', encoding='utf-8') as fh:
    targets = [line.strip() for line in fh if line.strip()]
payload = {
    "issue_id": int(issue_id),
    "ok": ok_flag == "1",
    "reason": reason,
    "mode": mode,
    "blocking": mode == "blocking",
    "process_contract_scope": process_scope == "1",
    "updated_files": [],
    "scope_files": scope,
    "doc_targets": targets,
    "recommended_targets": targets,
    "artifact_dir": artifact_dir,
}
with open(summary_path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(json.dumps(payload, ensure_ascii=False))
PY
}

if [[ ${#doc_targets[@]} -eq 0 ]]; then
  emit_summary "NO_TARGETS" 1
  exit 0
fi

if [[ "$effective_mode" == "advisory" ]]; then
  emit_summary "ADVISORY_ONLY" 1
  exit 0
fi

if [[ "$doc_targets_already_in_scope" -eq 1 ]]; then
  emit_summary "ALREADY_IN_SCOPE" 1
  exit 0
fi

if [[ -z "$codex_bin" || ! -x "$codex_bin" ]]; then
  echo "[CODEX_MISSING] codex CLI is required for docs sync gate" >&2
  exit 2
fi

initial_targets_snapshot="$artifact_dir/targets_initial.json"
hash_snapshot "$initial_targets_snapshot" "${doc_targets[@]}"
feedback_path=""
attempt=1
final_reason="MAX_ATTEMPTS_EXCEEDED"
while [[ "$attempt" -le "$max_attempts" ]]; do
  writer_before="$artifact_dir/writer_before_${attempt}.json"
  writer_after="$artifact_dir/writer_after_${attempt}.json"
  writer_log="$artifact_dir/writer_attempt_${attempt}.log"
  writer_message="$artifact_dir/writer_attempt_${attempt}.txt"
  reviewer_log="$artifact_dir/reviewer_attempt_${attempt}.log"
  reviewer_json="$artifact_dir/reviewer_attempt_${attempt}.json"

  dirty_snapshot "$writer_before"
  feedback_block=""
  if [[ -n "$feedback_path" && -f "$feedback_path" ]]; then
    feedback_block=$'\nПредыдущий review:\n'"$(cat "$feedback_path")"
  fi

  writer_prompt="$(cat <<EOF
Ты выполняешь docs-sync для issue #$issue_id.

Изменённые файлы:
$(sed 's/^/- /' "$scope_file")

Целевые внутренние документы:
$(sed 's/^/- /' "$targets_file")

Ограничения:
- Можно читать и менять только scope files и перечисленные целевые документы.
- Нельзя трогать user-facing \`docs/**\`, кроме существующего release flow (он здесь не участвует).
- Используй в первую очередь встроенный ниже контекст файлов; не сканируй репозиторий целиком, не запускай браузер/MCP и не используй planning/user-input инструменты.
- Если на целевых документах уже есть активные lease той же issue от родительской сессии, это не конфликт: не пытайся брать новые lockctl-lock'и и считай эти файлы уже зарезервированными для текущего docs-sync запуска.
- Сначала самостоятельно сравни scope changes с target-документами и обнови их, если есть расхождения или упущения.
- Если ниже передан предыдущий review, используй его как дополнительную корректировку, но не жди review как единственный триггер записи.
- Не делай commit/push.

Контекст документов:
$(render_prompt_context "${doc_targets[@]}")
$feedback_block
EOF
)"

  if ! run_with_timeout "$codex_bin" exec --sandbox workspace-write --ephemeral --output-last-message "$writer_message" "$writer_prompt" >"$writer_log" 2>&1; then
    final_reason="WRITER_FAILED"
    break
  fi

  dirty_snapshot "$writer_after"
  if ! assert_only_targets_changed "$writer_before" "$writer_after" "$targets_file" >/dev/null; then
    final_reason="SCOPE_VIOLATION"
    break
  fi

  reviewer_prompt="$(cat <<EOF
Ты проверяешь результат docs-sync после writer-pass для issue #$issue_id.

Scope changes:
$(sed 's/^/- /' "$scope_file")

Documentation targets:
$(sed 's/^/- /' "$targets_file")

Правила:
- Работай только в read-only режиме.
- Используй в первую очередь встроенный ниже контекст файлов; не сканируй весь репозиторий без необходимости.
- Проверяй, что docs targets после writer-pass отражают текущие изменения достаточно полно и точно.
- Не требуй правок в user-facing \`docs/**\`, если речь про internal process/runtime docs.
- verdict=ok только если документация уже достаточна.
- verdict=request_changes только если в целевых документах всё ещё действительно нужны точечные правки.
- verdict=blocked если корректная оценка невозможна без бизнес-решения.
- Не возвращай свободный текст вне JSON и строго соблюдай output schema.

Контекст документов:
$(render_prompt_context "${doc_targets[@]}")
EOF
)"

  if ! run_with_timeout "$codex_bin" exec --sandbox read-only --ephemeral --output-schema "$schema_file" --output-last-message "$reviewer_json" "$reviewer_prompt" >"$reviewer_log" 2>&1; then
    final_reason="REVIEW_FAILED"
    break
  fi
  if [[ ! -s "$reviewer_json" ]]; then
    final_reason="REVIEW_FAILED"
    break
  fi

  verdict="$(review_verdict "$reviewer_json")"
  if [[ "$verdict" == "ok" ]]; then
    final_reason="OK"
    break
  fi
  if [[ "$verdict" == "blocked" ]]; then
    final_reason="REVIEW_BLOCKED"
    break
  fi

  feedback_path="$reviewer_json"
  attempt=$((attempt + 1))
done

final_targets_snapshot="$artifact_dir/targets_final.json"
hash_snapshot "$final_targets_snapshot" "${doc_targets[@]}"
mapfile -t changed_docs < <(changed_targets_from_snapshots "$initial_targets_snapshot" "$final_targets_snapshot")

python3 - "$summary_path" "$issue_id" "$scope_file" "$targets_file" "$artifact_dir" "$final_reason" "$effective_mode" "$scope_has_process_contract" "${changed_docs[@]}" <<'PY'
import json
import sys

summary_path, issue_id, scope_file, targets_file, artifact_dir, reason, mode, process_scope, *changed = sys.argv[1:]
with open(scope_file, 'r', encoding='utf-8') as fh:
    scope = [line.strip() for line in fh if line.strip()]
with open(targets_file, 'r', encoding='utf-8') as fh:
    targets = [line.strip() for line in fh if line.strip()]
payload = {
    "issue_id": int(issue_id),
    "ok": reason == "OK" or reason == "SKIPPED",
    "reason": reason,
    "mode": mode,
    "blocking": mode == "blocking",
    "process_contract_scope": process_scope == "1",
    "updated_files": [item for item in changed if item.strip()],
    "scope_files": scope,
    "doc_targets": targets,
    "recommended_targets": targets,
    "artifact_dir": artifact_dir,
}
with open(summary_path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(json.dumps(payload, ensure_ascii=False))
PY

[[ "$final_reason" == "OK" ]]
