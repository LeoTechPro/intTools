#!/usr/bin/env bash
set -euo pipefail

NEXUS_REPO_ROOT="${NEXUS_REPO_ROOT:-/int/nexus}"

pushd "$NEXUS_REPO_ROOT/web" >/dev/null
npm ci
npm run build
popd >/dev/null

rsync -az "$NEXUS_REPO_ROOT/web/.next/" /var/www/intdata-test/.next/
systemctl restart intdata-test-web
