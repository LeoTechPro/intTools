#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

# Safe queue-based autopush:
# - processes explicit request files from ~/.codex/tmp/punkt-b/autopush/
# - never uses git add -A
# - refuses to run if unrelated dirty files exist
# - refuses push when dev cannot be synced by fast-forward

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QUEUE_DIR="${AUTOPUSH_QUEUE_DIR:-$ops_runtime_root/autopush}"
REPORT_DIR="$QUEUE_DIR/reports"
LOG_PREFIX="[safe_autopush]"
CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_REVIEW_SCHEMA="${CODEX_REVIEW_SCHEMA:-$ops_home/templates/codex-review.schema.json}"
CODEX_TIMEOUT_SEC="${CODEX_TIMEOUT_SEC:-180}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-dev}"

mkdir -p "$QUEUE_DIR"
mkdir -p "$REPORT_DIR"

cd "$REPO_ROOT"

if [[ "${PUNKTB_GIT_APPROVED:-NO}" != "YES" ]]; then
  echo "$LOG_PREFIX refused: set PUNKTB_GIT_APPROVED=YES (owner-approved) to allow any git operations"
  exit 0
fi

if [[ "${ENABLE_SAFE_AUTOPUSH:-0}" != "1" ]]; then
  echo "$LOG_PREFIX disabled by default; set ENABLE_SAFE_AUTOPUSH=1 to run"
  exit 0
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "$LOG_PREFIX not a git repository: $REPO_ROOT" >&2
  exit 1
fi

shopt -s nullglob
requests=("$QUEUE_DIR"/*.env)

if [[ ${#requests[@]} -eq 0 ]]; then
  echo "$LOG_PREFIX no requests"
  exit 0
fi

process_one() {
  local req="$1"
  local base
  base="$(basename "$req")"

  # shellcheck source=/dev/null
  source "$req"

  : "${REQUEST_ID:?REQUEST_ID is required}"
  : "${ISSUE_ID:?ISSUE_ID is required}"
  : "${COMMIT_MESSAGE:?COMMIT_MESSAGE is required}"
  : "${FILES:?FILES is required (comma-separated paths)}"
  REQUEST_ID="${REQUEST_ID:-$base}"
  TARGET_BRANCH="${TARGET_BRANCH:-$DEFAULT_BRANCH}"

  if [[ "$TARGET_BRANCH" != "dev" ]]; then
    echo "$LOG_PREFIX $base rejected: TARGET_BRANCH must be dev" >&2
    mv "$req" "$QUEUE_DIR/${base}.rejected"
    return 0
  fi

  # Protect against dangerous patterns.
  if echo "$FILES" | grep -Eq '(^|,)(\.git/|\.beads/|backend/init/migrations/|docker-compose\.yaml)(,|$)'; then
    echo "$LOG_PREFIX $base rejected: forbidden paths in FILES" >&2
    mv "$req" "$QUEUE_DIR/${base}.rejected"
    return 0
  fi

  # Parse and validate target file list.
  IFS=',' read -r -a raw_files <<< "$FILES"
  declare -a files=()
  for f in "${raw_files[@]}"; do
    f="$(echo "$f" | sed 's/^ *//; s/ *$//')"
    [[ -z "$f" ]] && continue
    if [[ ! -e "$f" ]]; then
      echo "$LOG_PREFIX $base rejected: missing file $f" >&2
      mv "$req" "$QUEUE_DIR/${base}.rejected"
      return 0
    fi
    files+=("$f")
  done

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "$LOG_PREFIX $base rejected: empty files list" >&2
    mv "$req" "$QUEUE_DIR/${base}.rejected"
    return 0
  fi

  if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
    echo "$LOG_PREFIX $base blocked: codex CLI not found via CODEX_BIN=$CODEX_BIN" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  if [[ ! -f "$CODEX_REVIEW_SCHEMA" ]]; then
    echo "$LOG_PREFIX $base blocked: codex review schema not found: $CODEX_REVIEW_SCHEMA" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "$LOG_PREFIX $base blocked: jq is required for codex review parsing" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  # Ensure working tree doesn't contain unrelated changes.
  mapfile -t dirty < <(git status --porcelain | sed -E 's/^.. //')
  declare -A allow=()
  for f in "${files[@]}"; do allow["$f"]=1; done

  for d in "${dirty[@]}"; do
    # Handle rename format "a -> b" by checking destination.
    if [[ "$d" == *" -> "* ]]; then
      d="${d##* -> }"
    fi
    if [[ -z "${allow[$d]:-}" ]]; then
      echo "$LOG_PREFIX $base blocked: unrelated dirty file detected: $d" >&2
      mv "$req" "$QUEUE_DIR/${base}.blocked"
      return 0
    fi
  done

  # Codex local review gate: run review only on requested files diff.
  diff_text="$(git diff -- "${files[@]}")"
  if [[ -z "$diff_text" ]]; then
    echo "$LOG_PREFIX $base skipped: no diff in requested files"
    mv "$req" "$QUEUE_DIR/${base}.done"
    return 0
  fi

  # Keep prompt bounded for stable runtime.
  max_diff_chars=120000
  if [[ ${#diff_text} -gt $max_diff_chars ]]; then
    diff_text="${diff_text:0:$max_diff_chars}\n\n[truncated]"
  fi

  review_prompt=$(
    cat <<PROMPT
Ты выполняешь строгий код-ревью для автопуша.
Верни JSON СТРОГО по схеме.
Критерий fail: есть хотя бы один критичный или высокий риск регрессии/безопасности/доступов.
Если таких рисков нет, decision=pass.

DIFF:
$diff_text
PROMPT
  )

  review_out="$REPORT_DIR/${REQUEST_ID}.json"
  review_log="$REPORT_DIR/${REQUEST_ID}.log"
  if ! timeout "$CODEX_TIMEOUT_SEC" "$CODEX_BIN" exec \
    --sandbox read-only \
    --output-schema "$CODEX_REVIEW_SCHEMA" \
    --output-last-message "$review_out" \
    "$review_prompt" >"$review_log" 2>&1; then
    echo "$LOG_PREFIX $base blocked: codex review failed or timed out" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  decision="$(jq -r '.decision // empty' "$review_out" 2>/dev/null || true)"
  critical_count="$(jq -r '.critical_count // -1' "$review_out" 2>/dev/null || true)"
  high_count="$(jq -r '.high_count // -1' "$review_out" 2>/dev/null || true)"
  summary="$(jq -r '.summary // \"\"' "$review_out" 2>/dev/null || true)"

  if [[ "$decision" != "pass" || "$critical_count" -gt 0 || "$high_count" -gt 0 ]]; then
    echo "$LOG_PREFIX $base blocked by codex review: decision=$decision critical=$critical_count high=$high_count" >&2
    echo "$LOG_PREFIX summary: $summary" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  before_sha="$(git rev-parse HEAD)"
  issue_commit_cmd=(bash "$ops_home/ops/issue/issue_commit.sh" --issue "$ISSUE_ID" --message "$COMMIT_MESSAGE")
  for f in "${files[@]}"; do
    issue_commit_cmd+=(--file "$f")
  done
  if ! "${issue_commit_cmd[@]}"; then
    echo "$LOG_PREFIX $base blocked: issue_commit.sh failed" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  if ! bash "$ops_home/ops/issue/issue_audit_local.sh" --range "${before_sha}..HEAD"; then
    echo "$LOG_PREFIX $base blocked: issue_audit_local failed" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi

  git fetch origin "$TARGET_BRANCH"
  if ! git merge --ff-only "refs/remotes/origin/$TARGET_BRANCH"; then
    echo "$LOG_PREFIX $base blocked: cannot fast-forward local $TARGET_BRANCH to origin/$TARGET_BRANCH" >&2
    mv "$req" "$QUEUE_DIR/${base}.blocked"
    return 0
  fi
  git push origin "$TARGET_BRANCH"

  mv "$req" "$QUEUE_DIR/${base}.done"
  echo "$LOG_PREFIX $base done"
}

# Process one request per run to minimize contention.
process_one "${requests[0]}"
