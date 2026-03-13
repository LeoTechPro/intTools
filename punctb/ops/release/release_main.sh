#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Usage:
  ops/release/release_main.sh --issue <release_issue_id> [--sha <commit>] [--repo owner/repo]

Flow:
1) fetch origin
2) validate release issue label/state
3) ensure target SHA is already in origin/dev and main update is fast-forward
4) run branch-aware main audit
5) push <sha>:main and close release issue
EOF
}

issue_id=""
target_sha=""
repo_arg=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --issue" >&2; exit 2; }
      issue_id="$2"
      shift 2
      ;;
    --sha)
      [[ $# -ge 2 ]] || { echo "[ARGUMENT] missing value for --sha" >&2; exit 2; }
      target_sha="$2"
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

if [[ "${PUNCTB_MAIN_PUSH_APPROVED:-NO}" != "YES" ]]; then
  echo "[MAIN_APPROVAL_REQUIRED] set PUNCTB_MAIN_PUSH_APPROVED=YES for release:main" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "[DIRTY_TREE] working tree is not clean; release:main requires a clean tree" >&2
  exit 2
fi

git -C "$repo_root" fetch origin --prune >/dev/null

repo_slug="$repo_arg"
if [[ -z "$repo_slug" ]]; then
  repo_slug="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi

issue_state="$(gh issue view "$issue_id" -R "$repo_slug" --json state --jq .state)"
if [[ "$issue_state" != "OPEN" ]]; then
  echo "[ISSUE_NOT_OPEN] release issue #${issue_id} must be OPEN" >&2
  exit 2
fi

labels_json="$(gh issue view "$issue_id" -R "$repo_slug" --json labels --jq '.labels[].name')"
if ! grep -qx 'release' <<< "$labels_json"; then
  echo "[RELEASE_LABEL_REQUIRED] release issue #${issue_id} must have label release" >&2
  exit 2
fi

dev_ref="refs/remotes/origin/dev"
main_ref="refs/remotes/origin/main"
if [[ -z "$target_sha" ]]; then
  target_sha="$(git -C "$repo_root" rev-parse "$dev_ref")"
else
  target_sha="$(git -C "$repo_root" rev-parse "$target_sha")"
fi
remote_main_sha="$(git -C "$repo_root" rev-parse "$main_ref")"

python3 "$ops_home/ops/issue/branch_policy_audit.py" assert-target \
  --target-branch main \
  --local-sha "$target_sha" \
  --remote-sha "$remote_main_sha" \
  --dev-ref "$dev_ref"

audit_range="${remote_main_sha}..${target_sha}"
bash "$ops_home/ops/gates/docs_boundary_guard.sh" --range "$audit_range" --allow-owner-override
python3 "$ops_home/ops/issue/branch_policy_audit.py" audit-range \
  --target-branch main \
  --range "$audit_range" \
  --repo "$repo_slug"

git -C "$repo_root" push origin "${target_sha}:main"

gh issue close "$issue_id" -R "$repo_slug" --comment "Released to main at ${target_sha}" >/dev/null

echo "RELEASE_MAIN_OK issue=#${issue_id} sha=${target_sha}"
