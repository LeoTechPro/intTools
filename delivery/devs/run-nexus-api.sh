#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

export INT_MODE="${INT_MODE:-suite}"
export AUTH_MODE="${AUTH_MODE:-centralized}"

BRAIN_REPO_ROOT="${BRAIN_REPO_ROOT:-/int/brain}"

cd "$BRAIN_REPO_ROOT"
uvicorn brain.api.main:app --host 0.0.0.0 --port 8080
