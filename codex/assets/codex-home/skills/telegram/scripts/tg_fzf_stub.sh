#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/.local/bin" "$HOME/.cache/tg"

cat > "$HOME/.local/bin/fzf" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
query=""
if [[ -n "${FZF_QUERY:-}" ]]; then
  query="$FZF_QUERY"
elif [[ -f "$HOME/.cache/tg/fzf_query" ]]; then
  query="$(cat "$HOME/.cache/tg/fzf_query" 2>/dev/null || true)"
fi

if [[ -n "$query" ]]; then
  awk -v q="$query" 'BEGIN{IGNORECASE=1} index($0,q){print; exit 0} END{exit 0}'
else
  awk 'NR==1{print; exit 0}'
fi
STUB

chmod +x "$HOME/.local/bin/fzf"

if [[ -n "${1:-}" ]]; then
  printf '%s' "$1" > "$HOME/.cache/tg/fzf_query"
fi

echo "[tg] fzf stub installed at ~/.local/bin/fzf"
if [[ -n "${1:-}" ]]; then
  echo "[tg] fzf_query set to: $1"
fi
