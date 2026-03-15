#!/usr/bin/env bash
set -euo pipefail

SESSION="${1:-tg-auth}"

# Prefer wrapper if present; fallback to python module.
TG_BIN="${TG_BIN:-$HOME/.local/bin/tg}"
if [[ ! -x "$TG_BIN" ]]; then
  TG_BIN="python3 -m tg"
fi

# Ensure dirs that tg expects exist (avoid noisy "find: ... No such file" output).
mkdir -p "$HOME/.cache/tg/files" "$HOME/.cache/tg/database" "$HOME/.local/share/tg" >/dev/null 2>&1 || true

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[tg] tmux session already exists: $SESSION"
  echo "[tg] attach: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" "$TG_BIN"
echo "[tg] started in tmux session: $SESSION"
echo "[tg] attach: tmux attach -t $SESSION"
echo "[tg] detach: Ctrl+b then d"

