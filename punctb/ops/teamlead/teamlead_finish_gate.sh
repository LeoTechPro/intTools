#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

repo_root="$(git rev-parse --show-toplevel)"
exec bash "$ops_home/ops/teamlead/teamlead_orchestrator.sh" --mode finish "$@"
