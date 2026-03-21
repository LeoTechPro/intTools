#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="/int/tools/codex"
SYSTEMD_ROOT="$HOME/.config/systemd/user"
CANONICAL_SYSTEMD="$SCRIPT_ROOT/systemd"

mkdir -p "$SYSTEMD_ROOT" /int/.runtime/cloud-access/cache /int/.runtime/cloud-access/log /int/cloud/gdrive /int/cloud/yadisk

ln -sfn "$CANONICAL_SYSTEMD/rclone-mount-gdrive.service" "$SYSTEMD_ROOT/rclone-mount-gdrive.service"
ln -sfn "$CANONICAL_SYSTEMD/rclone-mount-yadisk.service" "$SYSTEMD_ROOT/rclone-mount-yadisk.service"

"$SCRIPT_ROOT/cloud_access.sh" ensure-dirs
systemctl --user daemon-reload

cat <<'EOF'
Cloud access runtime is prepared.

Next steps:
  1. Run `/int/tools/codex/cloud_access.sh config`
  2. Create remotes `gdrive` (drive) and `yadisk` (yandex)
  3. Start the mounts:
     systemctl --user start rclone-mount-gdrive.service
     systemctl --user start rclone-mount-yadisk.service
EOF
