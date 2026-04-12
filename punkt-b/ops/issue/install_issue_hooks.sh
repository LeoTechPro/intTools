#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

repo_root="$(git rev-parse --show-toplevel)"

mkdir -p "$ops_home/git-hooks"

for hook in commit-msg pre-push post-commit reference-transaction; do
  if [[ ! -f "$ops_home/git-hooks/$hook" ]]; then
    echo "[MISSING_HOOK] $ops_home/git-hooks/$hook" >&2
    exit 2
  fi
  chmod +x "$ops_home/git-hooks/$hook"
done

git -C "$repo_root" config core.hooksPath "$ops_home/git-hooks"
hooks_path="$(git -C "$repo_root" config --get core.hooksPath || true)"
if [[ "$hooks_path" != "$ops_home/git-hooks" ]]; then
  echo "[HOOKS_PATH_MISMATCH] expected $ops_home/git-hooks, got: ${hooks_path:-<empty>}" >&2
  exit 2
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "[GH_AUTH] gh is not authenticated; run 'gh auth login' before commits/pushes" >&2
  exit 2
fi

echo "HOOKS_INSTALLED core.hooksPath=${hooks_path} hooks=commit-msg,pre-push,post-commit,reference-transaction gh_auth=ok"
