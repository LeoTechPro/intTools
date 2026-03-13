#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/gates/autoreview_gate.sh --issue <id> --files "path1,path2"
  ops/gates/autoreview_gate.sh --issue <id> --file path1 --file path2
  ops/gates/autoreview_gate.sh --issue <id> --range <git-range>

Options:
  --issue <id>          Explicit numeric GitHub issue id.
  --files <csv>         Comma-separated file paths.
  --file <path>         Repeatable file path argument.
  --range <git-range>   Git range used to derive review scope.
  --max-attempts <n>    Auto-fix attempt cap (default: 1).
EOF
}

issue_id=""
files_csv=""
range_arg=""
max_attempts="${AUTOREVIEW_MAX_ATTEMPTS:-1}"
reviewer_max_retries="${AUTOREVIEW_REVIEWER_MAX_RETRIES:-2}"
secondary_review="${AUTOREVIEW_SECOND_REVIEW:-NO}"
allow_fixer="${AUTOREVIEW_ALLOW_FIXER:-NO}"
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
    --range)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --range" >&2; exit 2; }
      range_arg="$2"
      shift 2
      ;;
    --max-attempts)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --max-attempts" >&2; exit 2; }
      max_attempts="$2"
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
if ! [[ "$max_attempts" =~ ^[1-9][0-9]*$ ]]; then
  echo "[INVALID_MAX_ATTEMPTS] expected positive integer, got: $max_attempts" >&2
  exit 2
fi
if ! [[ "$reviewer_max_retries" =~ ^[1-9][0-9]*$ ]]; then
  echo "[INVALID_REVIEWER_MAX_RETRIES] expected positive integer, got: $reviewer_max_retries" >&2
  exit 2
fi
if [[ "$secondary_review" != "YES" && "$secondary_review" != "NO" ]]; then
  echo "[INVALID_SECOND_REVIEW] expected YES|NO, got: $secondary_review" >&2
  exit 2
fi
if [[ "$allow_fixer" != "YES" && "$allow_fixer" != "NO" ]]; then
  echo "[INVALID_ALLOW_FIXER] expected YES|NO, got: $allow_fixer" >&2
  exit 2
fi

if [[ -n "$files_csv" && -n "$range_arg" ]]; then
  echo "[ARGUMENT] use either --files/--file or --range, not both" >&2
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

if [[ -n "$range_arg" ]]; then
  while IFS= read -r path; do
    [[ -n "$path" ]] && files+=("$path")
  done < <(git diff --name-only "$range_arg")
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "[ARGUMENT] at least one file must be provided via --files/--file or a non-empty --range" >&2
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

CODEX_BIN="${CODEX_BIN:-$(command -v codex || true)}"
SCHEMA_FILE="${AUTOREVIEW_SCHEMA_FILE:-$ops_home/templates/autoreview.schema.json}"
CODEX_TIMEOUT_SEC="${CODEX_TIMEOUT_SEC:-300}"
MATRIX_FILE="${SWARM_RISK_MATRIX_FILE:-$ops_home/templates/swarm-risk-matrix.yaml}"
MATRIX_HELPER="${SWARM_RISK_MATRIX_HELPER:-$ops_home/ops/teamlead/role_opinion_matrix.py}"

if [[ -z "$CODEX_BIN" || ! -x "$CODEX_BIN" ]]; then
  echo "[CODEX_MISSING] codex CLI is required for autoreview" >&2
  exit 2
fi
if [[ ! -f "$SCHEMA_FILE" ]]; then
  echo "[SCHEMA_MISSING] expected schema file: $SCHEMA_FILE" >&2
  exit 2
fi
if [[ ! -f "$MATRIX_FILE" ]]; then
  echo "[MATRIX_MISSING] expected risk matrix: $MATRIX_FILE" >&2
  exit 2
fi
if [[ ! -f "$MATRIX_HELPER" ]]; then
  echo "[MATRIX_HELPER_MISSING] expected matrix helper: $MATRIX_HELPER" >&2
  exit 2
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_dir="${AUTOREVIEW_ARTIFACT_DIR:-$ops_runtime_root/autoreview/${issue_id}/${timestamp}}"
mkdir -p "$artifact_dir"

summary_path="$artifact_dir/final-gate.json"
scope_file="$artifact_dir/scope-files.txt"
printf '%s\n' "${scope_files[@]}" > "$scope_file"

scope_has_web=0
scope_has_backend_functions=0
scope_has_docs=0
scope_has_process_contract=0
scope_all_process_contract=1
for scope_path in "${scope_files[@]}"; do
  if [[ "$scope_path" == web/* ]]; then
    scope_has_web=1
  fi
  if [[ "$scope_path" == backend/functions/* ]]; then
    scope_has_backend_functions=1
  fi
  if [[ "$scope_path" == docs/* ]]; then
    scope_has_docs=1
  fi
  if [[ "$scope_path" == README.md || "$scope_path" == package.json || "$scope_path" == ".gitignore" || "$scope_path" == AGENTS.md || "$scope_path" == GEMINI.md || "$scope_path" == openspec/* ]]; then
    scope_has_process_contract=1
  else
    scope_all_process_contract=0
  fi
done

run_with_timeout() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "$CODEX_TIMEOUT_SEC" "$@"
  else
    "$@"
  fi
}

json_escape_multiline() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

build_review_prompt() {
  local reviewer="$1"
  local attempt="$2"
  local retry="$3"
  local scope_lines
  scope_lines="$(sed 's/^/- /' "$scope_file")"
  local reviewer_blurb=""
  if [[ "$reviewer" == "reviewer_a" ]]; then
    reviewer_blurb="Ты reviewer A. Проведи максимально строгий adversarial code review по текущему состоянию дерева в рамках scope."
  else
    reviewer_blurb="Ты reviewer B. Игнорируй предыдущие выводы и независимо перепроверь текущее состояние дерева в рамках scope."
  fi

  cat <<EOF
$reviewer_blurb

Контекст:
- issue: #$issue_id
- attempt: $attempt
- transport retry: $retry
- repo root: $repo_root

Scope files:
$scope_lines

Правила:
- Работай только в read-only режиме.
- Проверяй только текущий код/скрипты/дифф по scope, но можешь читать соседний контекст для верификации.
- Не используй skills, MCP, браузер, web-поиск или внешние источники; достаточно локальных файлов, команды git diff и соседнего кода.
- Conventional checks уже выполнены отдельно gate-скриптом. Не запускай build/lint/test/typecheck команды (npm, pnpm, yarn, tsc, vite, vitest, eslint).
- Ограничься быстрым локальным чтением: git diff, git diff --stat, sed, rg, cat.
- Не предлагай «возможно». Либо есть конкретная проблема, либо verdict=ok.
- Считай багами: регрессии, неработающий shell flow, небезопасные обходы scope, пропущенные edge cases в gate logic, ложные зелёные статусы.
- Максимум 5 findings. Если существенных замечаний нет, сразу возвращай verdict=ok.
- Если замечаний нет, верни verdict=ok и пустой findings.
- Если есть хотя бы одно существенное замечание, верни verdict=request_changes.
- Если корректная проверка невозможна, верни verdict=blocked.
- Строго соблюдай JSON schema.
EOF
}

build_fix_prompt() {
  local source_report="$1"
  local attempt="$2"
  local reviewer="$3"
  local scope_lines
  scope_lines="$(sed 's/^/- /' "$scope_file")"
  local report_json
  report_json="$(cat "$source_report")"
  cat <<EOF
Исправь замечания $reviewer для issue #$issue_id.

Scope files:
$scope_lines

Ограничения:
- Можно менять только файлы из scope.
- Нельзя трогать unrelated dirty files вне scope.
- Нельзя добавлять обходной bypass вместо реальной логики gate.
- Не выполняй commit/push/merge.
- После правок оставь рабочее дерево в несстейдженном состоянии.

Отчёт reviewer:
$report_json
EOF
}

model_args() {
  local model="$1"
  if [[ -n "$model" ]]; then
    printf '%s\0%s\0' "-m" "$model"
  fi
}

run_reviewer() {
  local reviewer="$1"
  local attempt="$2"
  local model="$3"
  local report_path="$artifact_dir/${reviewer}_attempt_${attempt}.json"
  local log_path="$artifact_dir/${reviewer}_attempt_${attempt}.log"
  mapfile -d '' -t review_model_args < <(model_args "$model")
  local retry="1"
  while [[ "$retry" -le "$reviewer_max_retries" ]]; do
    local prompt
    prompt="$(build_review_prompt "$reviewer" "$attempt" "$retry")"
    : >"$log_path"
    rm -f "$report_path"

    if printf '%s' "$prompt" | run_with_timeout "$CODEX_BIN" exec \
      --sandbox read-only \
      --ephemeral \
      -c "model_reasoning_effort=\"${review_reasoning_effort}\"" \
      "${review_model_args[@]}" \
      --output-schema "$SCHEMA_FILE" \
      --output-last-message "$report_path" \
      - >"$log_path" 2>&1 && [[ -s "$report_path" ]] && python3 - "$report_path" "$reviewer" "$attempt" <<'PY'
import json, sys
path, reviewer, attempt = sys.argv[1:4]
with open(path, 'r', encoding='utf-8') as fh:
    payload = json.load(fh)
payload.setdefault("reviewer", reviewer)
payload.setdefault("attempt", int(attempt))
with open(path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY
    then
      return 0
    fi

    if [[ "$retry" -lt "$reviewer_max_retries" ]]; then
      {
        printf '\n[REVIEWER_RETRY] reviewer=%s attempt=%s retry=%s/%s\n' \
          "$reviewer" "$attempt" "$retry" "$reviewer_max_retries"
      } >>"$log_path"
    fi
    retry=$((retry + 1))
  done

  if [[ ! -f "$report_path" || ! -s "$report_path" ]]; then
    echo "[REVIEWER_FAILED] reviewer=$reviewer attempt=$attempt retries=$reviewer_max_retries log=$log_path" >&2
  else
    echo "[REVIEWER_INVALID_OUTPUT] reviewer=$reviewer attempt=$attempt retries=$reviewer_max_retries log=$log_path" >&2
  fi
  return 1
}

review_verdict() {
  python3 - "$1" <<'PY'
import json, sys
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

for finding in findings:
    if not isinstance(finding, dict):
        print("blocked")
        raise SystemExit(0)
    for key in ("severity", "title", "file", "details"):
        value = finding.get(key, "")
        if not isinstance(value, str) or not value.strip():
            print("blocked")
            raise SystemExit(0)

print(verdict)
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

assert_scope_clean() {
  local before_path="$1"
  local after_path="$2"
  python3 - "$before_path" "$after_path" "$scope_file" <<'PY'
import json
import sys

before_path, after_path, scope_path = sys.argv[1:4]
with open(before_path, 'r', encoding='utf-8') as fh:
    before = json.load(fh)
with open(after_path, 'r', encoding='utf-8') as fh:
    after = json.load(fh)
with open(scope_path, 'r', encoding='utf-8') as fh:
    scope = {line.strip() for line in fh if line.strip()}

bad = []
for path in sorted(set(before) | set(after)):
    if path in scope:
        continue
    if before.get(path) != after.get(path):
        bad.append(path)

if bad:
    print("\n".join(bad))
    sys.exit(1)
PY
}

run_fixer() {
  local reviewer="$1"
  local attempt="$2"
  local source_report="$3"
  local model="$4"
  local log_path="$artifact_dir/fixer_after_${reviewer}_attempt_${attempt}.log"
  local message_path="$artifact_dir/fixer_after_${reviewer}_attempt_${attempt}.txt"
  local before_snapshot="$artifact_dir/fixer_after_${reviewer}_attempt_${attempt}_before.json"
  local after_snapshot="$artifact_dir/fixer_after_${reviewer}_attempt_${attempt}_after.json"
  local prompt
  prompt="$(build_fix_prompt "$source_report" "$attempt" "$reviewer")"
  mapfile -d '' -t fix_model_args < <(model_args "$model")

  dirty_snapshot "$before_snapshot"

  if ! printf '%s' "$prompt" | run_with_timeout "$CODEX_BIN" exec \
    --sandbox workspace-write \
    --ephemeral \
    -c "model_reasoning_effort=\"${review_reasoning_effort}\"" \
    "${fix_model_args[@]}" \
    --output-last-message "$message_path" \
    - >"$log_path" 2>&1; then
    echo "[FIXER_FAILED] reviewer=$reviewer attempt=$attempt log=$log_path" >&2
    return 1
  fi

  dirty_snapshot "$after_snapshot"
  if ! assert_scope_clean "$before_snapshot" "$after_snapshot"; then
    echo "[SCOPE_VIOLATION] fixer touched files outside scope after reviewer=$reviewer attempt=$attempt" >&2
    return 1
  fi
}

required_checks_csv() {
  local files_arg="$1"
  python3 "$MATRIX_HELPER" --matrix "$MATRIX_FILE" --files "$files_arg" --field required_checks
}

collect_web_scope_paths() {
  local mode="$1"
  local scope_path=""
  local rel_path=""

  for scope_path in "${scope_files[@]}"; do
    [[ "$scope_path" == web/* ]] || continue
    rel_path="${scope_path#web/}"
    [[ -f "$repo_root/$scope_path" ]] || continue

    case "$mode" in
      lint)
        case "$rel_path" in
          *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
            printf '%s\n' "$rel_path"
            ;;
        esac
        ;;
      unit-tests)
        case "$rel_path" in
          tests/*)
            printf '%s\n' "$rel_path"
            ;;
        esac
        ;;
    esac
  done
}

run_check() {
  local check_id="$1"
  local out_path="$2"
  local status="passed"
  local detail=""

  case "$check_id" in
    lint)
      if [[ "$scope_has_web" -eq 1 || "$scope_has_docs" -eq 1 ]]; then
        mapfile -t lint_targets < <(collect_web_scope_paths lint)
        if [[ ${#lint_targets[@]} -eq 0 ]]; then
          printf 'No scoped web lint targets found.\n' >"$out_path"
          status="skipped"
          detail="no-scoped-web-lint-targets"
        else
          if ! {
            npm --prefix web run check:test-imports
            (
              cd "$repo_root/web"
              npx eslint --no-warn-ignored "${lint_targets[@]}"
            )
          } >"$out_path" 2>&1; then
            status="failed"
            detail="npm --prefix web run check:test-imports && (cd web && npx eslint --no-warn-ignored <scope>)"
          else
            detail="npm --prefix web run check:test-imports && (cd web && npx eslint --no-warn-ignored <scope>)"
          fi
        fi
      elif [[ "$scope_all_process_contract" -eq 1 ]]; then
        if ! python3 - "$out_path" "${scope_files[@]}" <<'PY'
import json
import pathlib
import subprocess
import sys

out_path = pathlib.Path(sys.argv[1])
files = [pathlib.Path(item) for item in sys.argv[2:]]
lines = []
failed = False

for rel in files:
    if rel.suffix == ".sh":
        cp = subprocess.run(["bash", "-n", str(rel)], text=True, capture_output=True)
        lines.append(f"$ bash -n {rel}")
        if cp.returncode != 0:
            failed = True
            lines.append(cp.stderr.strip() or cp.stdout.strip() or "bash -n failed")
    elif rel.suffix == ".json":
        try:
            json.loads(rel.read_text(encoding="utf-8"))
            lines.append(f"$ json ok {rel}")
        except Exception as exc:
            failed = True
            lines.append(f"$ json invalid {rel}: {exc}")
    else:
        lines.append(f"$ skip syntax lint {rel}")

out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
sys.exit(1 if failed else 0)
PY
        then
          status="failed"
          detail="agent-local syntax lint"
        else
          detail="agent-local syntax lint"
        fi
      else
        printf 'No dedicated lint runner is configured for this non-web scope.\n' >"$out_path"
        status="skipped"
        detail="no-non-web-lint-runner"
      fi
      ;;
    build)
      if [[ "$scope_has_web" -eq 1 || "$scope_has_docs" -eq 1 ]]; then
        if ! npm --prefix web run build >"$out_path" 2>&1; then
          status="failed"
          detail="npm --prefix web run build"
        else
          detail="npm --prefix web run build"
        fi
      else
        printf 'No dedicated build runner is configured for this scope.\n' >"$out_path"
        status="skipped"
        detail="no-build-runner"
      fi
      ;;
    unit)
      if printf '%s\n' "${scope_files[@]}" | grep -q '^web/'; then
        mapfile -t unit_test_targets < <(collect_web_scope_paths unit-tests)
        if [[ ${#unit_test_targets[@]} -eq 0 ]]; then
          printf 'No scoped web unit targets found.\n' >"$out_path"
          status="skipped"
          detail="no-scoped-web-unit-targets"
        else
          if ! {
            (
              cd "$repo_root/web"
              npx vitest run --passWithNoTests "${unit_test_targets[@]}"
            )
          } >"$out_path" 2>&1; then
            status="failed"
            detail="scoped vitest test-files run"
          else
            detail="scoped vitest test-files run"
          fi
        fi
      else
        printf 'No dedicated non-web unit runner is configured for this scope.\n' >"$out_path"
        status="skipped"
        detail="no-non-web-unit-runner"
      fi
      ;;
    integration)
      if printf '%s\n' "${scope_files[@]}" | grep -q '^backend/functions/'; then
        if [[ -z "${SERVICE_ROLE_KEY:-}" ]]; then
          printf 'SERVICE_ROLE_KEY is required for backend integration smoke.\n' >"$out_path"
          status="unavailable"
          detail="missing SERVICE_ROLE_KEY"
        elif ! bash "$ops_home/ops/qa/smoke_api_access.sh" >"$out_path" 2>&1; then
          status="failed"
          detail="bash ops/qa/smoke_api_access.sh"
        else
          detail="bash ops/qa/smoke_api_access.sh"
        fi
      elif printf '%s\n' "${scope_files[@]}" | grep -q '^web/'; then
        if ! MODE=handoff bash "$ops_home/ops/agent-browser/agent_browser_gate.sh" >"$out_path" 2>&1; then
          status="failed"
          detail="MODE=handoff bash ops/agent-browser/agent_browser_gate.sh"
        else
          detail="MODE=handoff bash ops/agent-browser/agent_browser_gate.sh"
        fi
      else
        printf 'Integration check is not required for this scope.\n' >"$out_path"
        status="skipped"
        detail="scope-has-no-integration-runner"
      fi
      ;;
    security)
      if ! bash "$ops_home/ops/qa/rbac_audit_gate.sh" >"$out_path" 2>&1; then
        status="failed"
        detail="bash ops/qa/rbac_audit_gate.sh"
      else
        detail="bash ops/qa/rbac_audit_gate.sh"
      fi
      ;;
    manual-review|llm-review-a|llm-review-b)
      printf 'Synthetic autoreview check: %s\n' "$check_id" >"$out_path"
      status="synthetic"
      detail="autofilled after reviewers"
      ;;
    migration-dry-run|rollback-rationale)
      printf 'Human migration gate is required for this scope.\n' >"$out_path"
      status="human_gate_required"
      detail="$check_id"
      ;;
    *)
      printf 'Unknown check id: %s\n' "$check_id" >"$out_path"
      status="failed"
      detail="unknown-check"
      ;;
  esac

  python3 - "$out_path" "$check_id" "$status" "$detail" <<'PY'
import json
import pathlib
import sys
payload = {
    "check_id": sys.argv[2],
    "status": sys.argv[3],
    "detail": sys.argv[4],
}
path = pathlib.Path(sys.argv[1] + ".meta.json")
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  [[ "$status" == "passed" || "$status" == "skipped" || "$status" == "synthetic" ]]
}

run_conventional_checks() {
  local attempt="$1"
  local checks_csv="$2"
  local -n passed_ref="$3"
  local -n failed_ref="$4"
  local -n unavailable_ref="$5"
  IFS=',' read -r -a required_checks <<< "$checks_csv"

  for check_id in "${required_checks[@]}"; do
    [[ -n "$check_id" ]] || continue
    case "$check_id" in
      manual-review|llm-review-a|llm-review-b)
        continue
        ;;
    esac

    local out_path="$artifact_dir/check_${check_id}_attempt_${attempt}.log"
    if run_check "$check_id" "$out_path"; then
      passed_ref+=("$check_id")
    else
      local status
      status="$(python3 - "$out_path.meta.json" <<'PY'
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    print(json.load(fh).get("status", "failed"))
PY
)"
      if [[ "$status" == "unavailable" || "$status" == "human_gate_required" ]]; then
        unavailable_ref+=("$check_id:$status")
      else
        failed_ref+=("$check_id")
      fi
    fi
  done
}

required_checks="$(required_checks_csv "$(IFS=,; echo "${scope_files[*]}")")"

if printf '%s\n' "${scope_files[@]}" | grep -q '^backend/init/migrations/'; then
  python3 - "$summary_path" "$issue_id" "$scope_file" <<'PY'
import json
import sys

summary_path, issue_id, scope_file = sys.argv[1:4]
with open(scope_file, 'r', encoding='utf-8') as fh:
    files = [line.strip() for line in fh if line.strip()]
payload = {
    "issue_id": int(issue_id),
    "ok": False,
    "reason": "HUMAN_GATE_REQUIRED",
    "files": files,
}
with open(summary_path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY
  echo "AUTOREVIEW_FAIL issue=#${issue_id} reason=HUMAN_GATE_REQUIRED summary=${summary_path}" >&2
  exit 1
fi

review_model="${AUTOREVIEW_REVIEW_MODEL:-${CODEX_MODEL:-}}"
fix_model="${AUTOREVIEW_FIX_MODEL:-${AUTOREVIEW_REVIEW_MODEL:-${CODEX_MODEL:-}}}"
review_reasoning_effort="${AUTOREVIEW_REVIEW_REASONING_EFFORT:-medium}"

attempt=1
final_reason="MAX_ATTEMPTS_EXCEEDED"
ok=0

while [[ "$attempt" -le "$max_attempts" ]]; do
  declare -a completed_checks=()
  declare -a failed_checks=()
  declare -a unavailable_checks=()

  run_conventional_checks "$attempt" "$required_checks" completed_checks failed_checks unavailable_checks

  if [[ ${#unavailable_checks[@]} -gt 0 ]]; then
    final_reason="CHECK_UNAVAILABLE"
    break
  fi
  if [[ ${#failed_checks[@]} -gt 0 ]]; then
    final_reason="CHECK_FAILED"
    break
  fi
  if ! run_reviewer "reviewer_a" "$attempt" "$review_model"; then
    final_reason="REVIEWER_A_FAILED"
    break
  fi
  reviewer_a_path="$artifact_dir/reviewer_a_attempt_${attempt}.json"
  reviewer_a_verdict="$(review_verdict "$reviewer_a_path")"

  if [[ "$reviewer_a_verdict" == "request_changes" ]]; then
    if [[ "$allow_fixer" == "YES" ]]; then
      if ! run_fixer "reviewer_a" "$attempt" "$reviewer_a_path" "$fix_model"; then
        final_reason="FIXER_AFTER_REVIEWER_A_FAILED"
        break
      fi
      attempt=$((attempt + 1))
      continue
    fi
    final_reason="REVIEWER_A_REQUEST_CHANGES"
    break
  fi
  if [[ "$reviewer_a_verdict" != "ok" ]]; then
    final_reason="REVIEWER_A_BLOCKED"
    break
  fi
  completed_checks+=("llm-review-a")

  if [[ "$secondary_review" != "YES" ]]; then
    ok=1
    final_reason="OK"
    break
  fi

  if ! run_reviewer "reviewer_b" "$attempt" "$review_model"; then
    final_reason="REVIEWER_B_FAILED"
    break
  fi
  reviewer_b_path="$artifact_dir/reviewer_b_attempt_${attempt}.json"
  reviewer_b_verdict="$(review_verdict "$reviewer_b_path")"

  if [[ "$reviewer_b_verdict" == "request_changes" ]]; then
    if [[ "$allow_fixer" == "YES" ]]; then
      if ! run_fixer "reviewer_b" "$attempt" "$reviewer_b_path" "$fix_model"; then
        final_reason="FIXER_AFTER_REVIEWER_B_FAILED"
        break
      fi
      attempt=$((attempt + 1))
      continue
    fi
    final_reason="REVIEWER_B_REQUEST_CHANGES"
    break
  fi
  if [[ "$reviewer_b_verdict" != "ok" ]]; then
    final_reason="REVIEWER_B_BLOCKED"
    break
  fi

  completed_checks+=("llm-review-b" "manual-review")
  ok=1
  final_reason="OK"
  break
done

python3 - "$summary_path" "$issue_id" "$scope_file" "$required_checks" "$final_reason" "$artifact_dir" "$ok" "$attempt" <<'PY'
import json
import os
import sys

summary_path, issue_id, scope_file, required_checks, final_reason, artifact_dir, ok, attempt = sys.argv[1:9]
with open(scope_file, 'r', encoding='utf-8') as fh:
    files = [line.strip() for line in fh if line.strip()]

attempts = []
for name in sorted(os.listdir(artifact_dir)):
    if name.endswith(".meta.json") and name.startswith("check_"):
        with open(os.path.join(artifact_dir, name), 'r', encoding='utf-8') as fh:
            attempts.append(json.load(fh))

payload = {
    "issue_id": int(issue_id),
    "ok": ok == "1",
    "reason": final_reason,
    "attempts_used": int(attempt),
    "required_checks": [item for item in required_checks.split(",") if item],
    "files": files,
    "artifact_dir": artifact_dir,
    "checks": attempts,
}
with open(summary_path, 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY

if [[ "$ok" -eq 1 ]]; then
  echo "AUTOREVIEW_OK issue=#${issue_id} attempts=${attempt} summary=${summary_path}"
  exit 0
fi

echo "AUTOREVIEW_FAIL issue=#${issue_id} reason=${final_reason} attempts=${attempt} summary=${summary_path}" >&2
exit 1
