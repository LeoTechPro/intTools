#!/usr/bin/env bash
set -euo pipefail
BASE_BRANCH="main"
FILES=("README.md" "AGENTS.md")

git fetch --all --prune
git checkout "$BASE_BRANCH"
git pull --ff-only

branches=$(git for-each-ref --format='%(refname:short)' refs/remotes/origin \
  | sed 's#^origin/##' | grep -E '^(test|feature/)' || true)

for br in $branches; do
  echo ">> Sync into $br"
  git checkout "$br"
  git pull --ff-only || true
  for f in "${FILES[@]}"; do
    git checkout "$BASE_BRANCH" -- "$f"
    if ! git diff --quiet -- "$f"; then
      git add "$f"
      git commit -m "chore(sync): mirror $f from $BASE_BRANCH"
      git push origin "$br"
    fi
  done
done

git checkout "$BASE_BRANCH"
