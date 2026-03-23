#!/usr/bin/env bash
set -euo pipefail

BRAIN_REPO_ROOT="${BRAIN_REPO_ROOT:-/int/brain}"

pushd "$BRAIN_REPO_ROOT/web" >/dev/null
npm ci
npm run build
popd >/dev/null

rsync -az "$BRAIN_REPO_ROOT/web/.next/" /var/www/intdata-test/.next/
systemctl restart intdata-test-web
