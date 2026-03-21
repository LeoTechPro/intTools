#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

export INT_MODE="${INT_MODE:-suite}"
export AUTH_MODE="${AUTH_MODE:-centralized}"

NEXUS_REPO_ROOT="${NEXUS_REPO_ROOT:-/int/nexus}"

cd "$NEXUS_REPO_ROOT"
uvicorn nexus.api.main:app --host 0.0.0.0 --port 8080
