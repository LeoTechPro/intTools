#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PUNKTB_OPS_HOME:-}" ]]; then
  ops_home="${PUNKTB_OPS_HOME}"
else
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  case "$script_dir" in
    */ops/*)
      ops_home="$(cd "$script_dir/../.." && pwd)"
      ;;
    */int-hooks)
      ops_home="$(cd "$script_dir/.." && pwd)"
      ;;
    *)
      ops_home="/int/tools/punkt-b"
      ;;
  esac
fi

repo_root="${PUNKTB_REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ops_runtime_root="${PUNKTB_OPS_RUNTIME_ROOT:-$HOME/.codex/tmp/punkt-b}"

export PUNKTB_OPS_HOME="$ops_home"
export PUNKTB_REPO_ROOT="$repo_root"
export PUNKTB_OPS_RUNTIME_ROOT="$ops_runtime_root"

mkdir -p "$ops_runtime_root"
