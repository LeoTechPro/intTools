#!/usr/bin/env bash
set -euo pipefail
BASE_BRANCH="main"
FILE="AGENTS.md"

git fetch origin --prune

git checkout "$BASE_BRANCH"
git pull --ff-only

branches=$(git for-each-ref --format='%(refname:short)' refs/remotes/origin \
  | sed 's#^origin/##' \
  | grep -E '^(test|feature/)' || true)

for br in $branches; do
  echo ">> Sync $FILE into $br"
  worktree_path=$(git worktree list --porcelain | awk -v b="refs/heads/${br}" 'BEGIN{path=""} /^worktree /{path=$2} /^branch /{if ($2==b){print path; exit}}')
  if [ -n "$worktree_path" ]; then
    git -C "$worktree_path" pull --ff-only || true
    git -C "$worktree_path" checkout "$BASE_BRANCH" -- "$FILE"
    if ! git -C "$worktree_path" diff --quiet -- "$FILE"; then
      git -C "$worktree_path" add "$FILE"
      git -C "$worktree_path" commit -m "chore(sync): mirror AGENTS.md from $BASE_BRANCH"
      git -C "$worktree_path" push origin "$br"
    else
      echo "   $br already up-to-date"
    fi
  else
    git checkout "$br"
    git pull --ff-only || true
    git checkout "$BASE_BRANCH" -- "$FILE"
    if ! git diff --quiet -- "$FILE"; then
      git add "$FILE"
      git commit -m "chore(sync): mirror AGENTS.md from $BASE_BRANCH"
      git push origin "$br"
    else
      echo "   $br already up-to-date"
    fi
  fi
done

git checkout "$BASE_BRANCH"
