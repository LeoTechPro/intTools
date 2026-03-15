#!/usr/bin/env bash
set -euo pipefail

systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
systemctl --user status openclaw-gateway.service --no-pager -n 20
