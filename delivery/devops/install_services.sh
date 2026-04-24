#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 0) Определяем файл окружения.
ENV_FILE_INPUT="${1:-}"
if [[ -n "$ENV_FILE_INPUT" ]]; then
  ENV_FILE="$ENV_FILE_INPUT"
fi

if [[ -z "${ENV_FILE:-}" ]]; then
  ENV_FILE="${ENV_FILE:-}"
  if [[ -z "$ENV_FILE" && -f "/int/brain/.env" ]]; then
    ENV_FILE="/int/brain/.env"
  fi
fi

if [[ -z "${ENV_FILE:-}" ]]; then
  echo "ERROR: ENV_FILE not specified and /int/brain/.env not found" >&2
  exit 1
fi

if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="$PROJECT_ROOT/$ENV_FILE"
fi

[ -s "$ENV_FILE" ] || { echo "ERROR: ENV_FILE missing or empty: $ENV_FILE" >&2; exit 1; }
export ENV_FILE

# 1) Подтягиваем только нужные переменные из ENV_FILE (без экспорта «всего»)
PROJECT_DIR=$(grep -E '^PROJECT_DIR=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d '\r')
PROJECT_VENV=$(grep -E '^PROJECT_VENV=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d '\r')
# expand nested refs like ${PROJECT_DIR}/venv
PROJECT_DIR=$(eval echo "$PROJECT_DIR")
PROJECT_VENV=$(eval echo "$PROJECT_VENV")

if [[ -z "$PROJECT_DIR" ]]; then
  PROJECT_DIR="$PROJECT_ROOT"
fi

[ -n "$PROJECT_VENV" ] || { echo "ERROR: PROJECT_VENV not set in $ENV_FILE" >&2; exit 1; }

# 2) Подготовка venv и зависимости
mkdir -p "$PROJECT_DIR"
python3 -m venv "$PROJECT_VENV" >/dev/null 2>&1 || true
"$PROJECT_VENV/bin/pip" install --upgrade pip
"$PROJECT_VENV/bin/pip" install -r requirements.txt

# 3) Установка unit-файлов (только если изменились)
#install -m 0644 -D "$PROJECT_ROOT/configs/systemd/intdata-web.service" /etc/systemd/system/intdata-web.service

# 4) Проверка синтаксиса и перезагрузка конфигурации systemd
systemd-analyze verify /etc/systemd/system/intdata-*.service /etc/systemd/system/nexus-intdata-*.service
systemctl daemon-reload

# 5) Включаем, но НЕ рестартим здесь (перезапуск сделает GitHub job один раз)
systemctl enable intdata-web.service

echo "install_services: ok"
