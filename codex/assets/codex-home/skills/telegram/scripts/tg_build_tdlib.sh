#!/usr/bin/env bash
set -euo pipefail

# Build TDLib (libtdjson.so) against system OpenSSL (e.g. OpenSSL 3 on Debian 13)
# and register it for `tg` via ~/.config/tg/conf.py (TDLIB_PATH=...).
#
# This is only needed when the bundled libtdjson from python-telegram fails with:
#   OSError: libssl.so.1.1: cannot open shared object file
#
# Safety:
# - Works in user directories under $HOME/.local
# - Network operations (git clone) happen only if the source dir is missing.

TD_SRC_DIR="${TD_SRC_DIR:-$HOME/.local/src/td}"
TD_BUILD_DIR="${TD_BUILD_DIR:-$TD_SRC_DIR/build}"
TD_INSTALL_DIR="${TD_INSTALL_DIR:-$HOME/.local/lib/tdlib}"
TD_INSTALL_LIB="${TD_INSTALL_LIB:-$TD_INSTALL_DIR/libtdjson.so}"
TG_CONF="${TG_CONF:-$HOME/.config/tg/conf.py}"

echo "[tdlib-build] target lib: $TD_INSTALL_LIB"
echo "[tdlib-build] tg conf:     $TG_CONF"
echo

if ! command -v cmake >/dev/null 2>&1 || ! command -v g++ >/dev/null 2>&1; then
  echo "[tdlib-build] ERROR: missing build tools (cmake/g++)."
  echo "[tdlib-build] Debian example:"
  echo "  sudo apt-get update"
  echo "  sudo apt-get install -y git cmake g++ make gperf pkg-config zlib1g-dev libssl-dev"
  exit 2
fi

if [[ ! -d "$TD_SRC_DIR/.git" ]]; then
  echo "[tdlib-build] cloning tdlib/td into: $TD_SRC_DIR"
  mkdir -p "$(dirname "$TD_SRC_DIR")"
  git clone --depth 1 https://github.com/tdlib/td.git "$TD_SRC_DIR"
else
  echo "[tdlib-build] tdlib source exists, skipping clone (no network fetch)."
fi

mkdir -p "$TD_BUILD_DIR"
echo "[tdlib-build] configuring (cmake) ..."
cmake -S "$TD_SRC_DIR" -B "$TD_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$HOME/.local"

echo "[tdlib-build] building target tdjson ..."
cmake --build "$TD_BUILD_DIR" --target tdjson -j"$(nproc)"

mkdir -p "$TD_INSTALL_DIR"
install -m 755 "$TD_BUILD_DIR/libtdjson.so" "$TD_INSTALL_LIB"
echo "[tdlib-build] installed: $TD_INSTALL_LIB"

mkdir -p "$(dirname "$TG_CONF")"
if [[ ! -f "$TG_CONF" ]]; then
  echo "[tdlib-build] ERROR: $TG_CONF отсутствует."
  echo "[tdlib-build] Сначала запусти интерактивный `tg`, чтобы он создал конфиг (и записал PHONE)."
  exit 3
fi

if rg -n "^TDLIB_PATH\\s*=" "$TG_CONF" >/dev/null 2>&1; then
  # Replace existing line (keep file format simple).
  tmp="$(mktemp)"
  rg -n "^TDLIB_PATH\\s*=" "$TG_CONF" >/dev/null || true
  awk -v p="$TD_INSTALL_LIB" '
    BEGIN { done=0 }
    /^TDLIB_PATH[[:space:]]*=/ {
      print "TDLIB_PATH = \047" p "\047"
      done=1
      next
    }
    { print }
    END {
      if (done==0) print "TDLIB_PATH = \047" p "\047"
    }
  ' "$TG_CONF" > "$tmp"
  mv "$tmp" "$TG_CONF"
else
  printf "\nTDLIB_PATH = '%s'\n" "$TD_INSTALL_LIB" >> "$TG_CONF"
fi

echo "[tdlib-build] updated TDLIB_PATH in $TG_CONF"
echo "[tdlib-build] done"

