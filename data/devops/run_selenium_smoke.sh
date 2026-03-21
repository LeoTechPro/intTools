#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/venv"
REQUIREMENTS_FILE="${ROOT_DIR}/tests/requirements.txt"
PYTEST_BIN="${VENV_DIR}/bin/pytest"
SELENIUM_MARKER="selenium"
TEST_PATH="tests/web/test_ui_selenium_smoke.py"

log() {
  printf '[selenium-smoke] %s\n' "$*"
}

if [[ ! -d "${VENV_DIR}" ]]; then
  log "Создаю виртуальное окружение (${VENV_DIR})."
  python3 -m venv "${VENV_DIR}"
fi

log "Обновляю pip/setuptools."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools >/dev/null

log "Устанавливаю зависимости из ${REQUIREMENTS_FILE}."
"${VENV_DIR}/bin/pip" install -r "${REQUIREMENTS_FILE}" >/dev/null

export CHROME_BINARY="${CHROME_BINARY:-/usr/bin/chromium}"
log "Использую браузер: ${CHROME_BINARY}"

export SELENIUM_WAIT_TIMEOUT="${SELENIUM_WAIT_TIMEOUT:-20}"
log "Таймаут ожидания: ${SELENIUM_WAIT_TIMEOUT} секунд"

log "Запускаю pytest -m ${SELENIUM_MARKER} ${TEST_PATH}"
"${PYTEST_BIN}" -m "${SELENIUM_MARKER}" "${ROOT_DIR}/${TEST_PATH}" "$@"

log "Smoke завершён. Скриншоты (если созданы) находятся в tests/web/screenshots/."
