#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/tools/openspec"
npm ci

bash "$ROOT_DIR/../lockctl/install_lockctl.sh"

echo "Готово. Используйте локальную команду:"
echo "  $ROOT_DIR/bin/openspec --version"
