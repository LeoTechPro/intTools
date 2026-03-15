#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="${CLOUD_ACCESS_ROOT:-/git/.runtime/cloud-access}"
RCLONE_CONFIG="${RCLONE_CONFIG:-$RUNTIME_ROOT/rclone.conf}"
CACHE_DIR="${CLOUD_ACCESS_CACHE_DIR:-$RUNTIME_ROOT/cache}"
LOG_DIR="${CLOUD_ACCESS_LOG_DIR:-$RUNTIME_ROOT/log}"
MOUNT_ROOT="${CLOUD_ACCESS_MOUNT_ROOT:-/git/cloud}"
VFS_CACHE_MODE="${CLOUD_ACCESS_VFS_CACHE_MODE:-writes}"
VFS_CACHE_MAX_SIZE="${CLOUD_ACCESS_VFS_CACHE_MAX_SIZE:-512M}"
BUFFER_SIZE="${CLOUD_ACCESS_BUFFER_SIZE:-4M}"
DIR_CACHE_TIME="${CLOUD_ACCESS_DIR_CACHE_TIME:-10m}"
POLL_INTERVAL="${CLOUD_ACCESS_POLL_INTERVAL:-0}"
LOG_LEVEL="${CLOUD_ACCESS_LOG_LEVEL:-INFO}"

usage() {
  cat <<'EOF'
Usage:
  cloud_access.sh ensure-dirs
  cloud_access.sh config
  cloud_access.sh list-remotes
  cloud_access.sh config-check [remote]
  cloud_access.sh auth-hint [remote]
  cloud_access.sh mount <remote> <mountpoint>
  cloud_access.sh umount <mountpoint>
EOF
}

ensure_dirs() {
  mkdir -p "$CACHE_DIR" "$LOG_DIR" "$MOUNT_ROOT/gdrive" "$MOUNT_ROOT/yadisk"
  if [[ ! -e "$RCLONE_CONFIG" ]]; then
    cat >"$RCLONE_CONFIG" <<'EOF'
# Managed by /git/tools/codex/cloud_access.sh
# Run `RCLONE_CONFIG=/git/.runtime/cloud-access/rclone.conf rclone config`
# to create the `gdrive` and `yadisk` remotes with headless OAuth.
EOF
  fi
  chmod 600 "$RCLONE_CONFIG"
}

list_remotes() {
  env RCLONE_CONFIG="$RCLONE_CONFIG" rclone listremotes
}

config_check() {
  local remote="${1:-}"

  ensure_dirs
  if [[ ! -s "$RCLONE_CONFIG" ]]; then
    echo "rclone config is empty: $RCLONE_CONFIG" >&2
    return 3
  fi

  if [[ -z "$remote" ]]; then
    list_remotes
    return 0
  fi

  if list_remotes | grep -Fxq "${remote}:"; then
    return 0
  fi

  echo "missing remote ${remote} in $RCLONE_CONFIG" >&2
  return 3
}

auth_hint() {
  local remote="${1:-all}"
  cat <<EOF
RCLONE_CONFIG=$RCLONE_CONFIG rclone config

Expected remotes:
  gdrive  -> type=drive
  yadisk  -> type=yandex

Target requested:
  $remote
EOF
}

mount_remote() {
  local remote="${1:?remote is required}"
  local mountpoint="${2:?mountpoint is required}"
  local log_file="$LOG_DIR/${remote}.log"

  ensure_dirs
  config_check "$remote"
  mkdir -p "$mountpoint"

  exec env RCLONE_CONFIG="$RCLONE_CONFIG" rclone mount "${remote}:" "$mountpoint" \
    --config "$RCLONE_CONFIG" \
    --cache-dir "$CACHE_DIR" \
    --vfs-cache-mode "$VFS_CACHE_MODE" \
    --vfs-cache-max-size "$VFS_CACHE_MAX_SIZE" \
    --buffer-size "$BUFFER_SIZE" \
    --dir-cache-time "$DIR_CACHE_TIME" \
    --poll-interval "$POLL_INTERVAL" \
    --log-level "$LOG_LEVEL" \
    --log-file "$log_file"
}

umount_remote() {
  local mountpoint="${1:?mountpoint is required}"
  if command -v fusermount3 >/dev/null 2>&1; then
    exec fusermount3 -u "$mountpoint"
  fi
  exec fusermount -u "$mountpoint"
}

command="${1:-}"
shift || true

case "$command" in
  ensure-dirs)
    ensure_dirs
    ;;
  config)
    ensure_dirs
    exec env RCLONE_CONFIG="$RCLONE_CONFIG" rclone config "$@"
    ;;
  list-remotes)
    list_remotes
    ;;
  config-check)
    config_check "${1:-}"
    ;;
  auth-hint)
    auth_hint "${1:-all}"
    ;;
  mount)
    mount_remote "$@"
    ;;
  umount)
    umount_remote "$@"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
