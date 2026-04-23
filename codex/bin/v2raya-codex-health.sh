#!/bin/sh
set -eu

CODEX_USER="${V2RAYA_CODEX_USER:-agents}"
REPO_ROOT="${V2RAYA_CODEX_REPO_ROOT:-/int/tools}"
SNAP_DATA="${V2RAYA_SNAP_DATA:-/var/snap/v2raya/current}"
HOOK_SOURCE="${V2RAYA_CORE_HOOK_SOURCE:-$REPO_ROOT/codex/bin/v2raya-core-hook-remove-quic.sh}"
HOOK_TARGET="${V2RAYA_CORE_HOOK_TARGET:-$SNAP_DATA/etc/core-hook-remove-quic.sh}"
V2RAYA_DROPIN_DIR="/etc/systemd/system/snap.v2raya.v2raya.service.d"
V2RAYA_DROPIN="$V2RAYA_DROPIN_DIR/10-codex-core-hook.conf"
CODEX_DROPIN_DIR="/home/$CODEX_USER/.config/systemd/user/codex-app-server.service.d"
CODEX_DROPIN="$CODEX_DROPIN_DIR/10-v2ray-proxy.conf"
HTTP_PROXY_URL="${V2RAYA_CODEX_HTTP_PROXY:-http://127.0.0.1:20171}"
SOCKS_PROXY_URL="${V2RAYA_CODEX_SOCKS_PROXY:-socks5h://127.0.0.1:20170}"
NO_PROXY_VALUE="${V2RAYA_CODEX_NO_PROXY:-127.0.0.1,localhost,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}"
CHATGPT_RESPONSES_URL="${V2RAYA_CODEX_RESPONSES_URL:-https://chatgpt.com/backend-api/codex/responses}"
CHATGPT_TRACE_URL="${V2RAYA_CODEX_TRACE_URL:-https://chatgpt.com/cdn-cgi/trace}"

log() {
  printf '%s %s\n' "$(date -Is)" "$*"
}

write_if_changed() {
  target="$1"
  mode="$2"
  tmp="${target}.tmp.$$"
  cat > "$tmp"
  if [ ! -f "$target" ] || ! cmp -s "$target" "$tmp"; then
    install -m "$mode" "$tmp" "$target"
    changed=1
  fi
  rm -f "$tmp"
}

run_user_systemctl() {
  uid="$(id -u "$CODEX_USER")"
  runuser -u "$CODEX_USER" -- env XDG_RUNTIME_DIR="/run/user/$uid" systemctl --user "$@"
}

port_listening() {
  port="$1"
  ss -ltn "sport = :$port" 2>/dev/null | grep -q "127.0.0.1:$port"
}

codex_proxy_env_ok() {
  pids="$(pgrep -u "$CODEX_USER" -f 'codex.*app-server|node .*codex app-server' || true)"
  [ -n "$pids" ] || return 1
  for pid in $pids; do
    env_dump="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null || true)"
    if printf '%s\n' "$env_dump" | grep -Fxq "HTTP_PROXY=$HTTP_PROXY_URL" &&
      printf '%s\n' "$env_dump" | grep -Fxq "HTTPS_PROXY=$HTTP_PROXY_URL" &&
      printf '%s\n' "$env_dump" | grep -Fxq "ALL_PROXY=$SOCKS_PROXY_URL" &&
      printf '%s\n' "$env_dump" | grep -Fxq "NO_PROXY=$NO_PROXY_VALUE"; then
      return 0
    fi
  done
  return 1
}

proxied_responses_ok() {
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' --max-time 20 --proxy "$HTTP_PROXY_URL" -I "$CHATGPT_RESPONSES_URL" 2>/dev/null || true)"
  [ "$code" = "405" ] || [ "$code" = "401" ] || [ "$code" = "404" ]
}

proxied_trace_ok() {
  curl -k -fsS --max-time 20 --proxy "$HTTP_PROXY_URL" "$CHATGPT_TRACE_URL" >/dev/null 2>&1
}

changed=0
restart_v2raya=0
restart_codex=0

if [ ! -x "$HOOK_SOURCE" ]; then
  log "missing hook source: $HOOK_SOURCE"
  exit 1
fi

install -d -m 0755 "$(dirname "$HOOK_TARGET")"
if [ ! -f "$HOOK_TARGET" ] || ! cmp -s "$HOOK_SOURCE" "$HOOK_TARGET"; then
  install -m 0755 "$HOOK_SOURCE" "$HOOK_TARGET"
  changed=1
  restart_v2raya=1
fi

install -d -m 0755 "$V2RAYA_DROPIN_DIR"
write_if_changed "$V2RAYA_DROPIN" 0644 <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/snap run v2raya --core-hook $HOOK_TARGET
EOF

install -d -m 0755 "$CODEX_DROPIN_DIR"
write_if_changed "$CODEX_DROPIN" 0644 <<EOF
[Service]
Environment=HTTP_PROXY=$HTTP_PROXY_URL
Environment=HTTPS_PROXY=$HTTP_PROXY_URL
Environment=ALL_PROXY=$SOCKS_PROXY_URL
Environment=NO_PROXY=$NO_PROXY_VALUE
ExecStartPre=/bin/sh -c 'curl -fsS --max-time 20 --proxy $HTTP_PROXY_URL https://chatgpt.com/cdn-cgi/trace >/dev/null'
EOF
chown -R "$CODEX_USER:$CODEX_USER" "/home/$CODEX_USER/.config/systemd/user"

if [ "$changed" -eq 1 ]; then
  systemctl daemon-reload
  run_user_systemctl daemon-reload || true
fi

if [ -f "$SNAP_DATA/etc/config.json" ] && grep -q '"quic"' "$SNAP_DATA/etc/config.json"; then
  "$HOOK_TARGET" || true
  restart_v2raya=1
fi

if ! pgrep -x v2ray >/dev/null 2>&1; then
  restart_v2raya=1
fi

if ! port_listening 20170 || ! port_listening 20171; then
  restart_v2raya=1
fi

if [ "$restart_v2raya" -eq 1 ]; then
  log "restarting snap.v2raya.v2raya.service"
  systemctl restart snap.v2raya.v2raya.service
  sleep 5
fi

if ! proxied_trace_ok || ! proxied_responses_ok; then
  log "retrying v2raya restart after failed proxied smoke"
  systemctl restart snap.v2raya.v2raya.service
  sleep 8
fi

if ! codex_proxy_env_ok; then
  restart_codex=1
fi

if [ "$restart_codex" -eq 1 ]; then
  log "restarting $CODEX_USER codex-app-server.service"
  run_user_systemctl restart codex-app-server.service
  sleep 3
fi

port_listening 20170
port_listening 20171
pgrep -x v2ray >/dev/null
proxied_trace_ok
proxied_responses_ok
codex_proxy_env_ok

log "v2raya/codex health ok"
