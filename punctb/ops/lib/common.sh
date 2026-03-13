#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PUNCTB_OPS_HOME:-}" ]]; then
  ops_home="${PUNCTB_OPS_HOME}"
else
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  case "$script_dir" in
    */ops/*)
      ops_home="$(cd "$script_dir/../.." && pwd)"
      ;;
    */git-hooks)
      ops_home="$(cd "$script_dir/.." && pwd)"
      ;;
    *)
      ops_home="/git/scripts/punctb"
      ;;
  esac
fi

repo_root="${PUNCTB_REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ops_runtime_root="${PUNCTB_OPS_RUNTIME_ROOT:-$HOME/.codex/tmp/punctb}"

export PUNCTB_OPS_HOME="$ops_home"
export PUNCTB_REPO_ROOT="$repo_root"
export PUNCTB_OPS_RUNTIME_ROOT="$ops_runtime_root"

mkdir -p "$ops_runtime_root"
