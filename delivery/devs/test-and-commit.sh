#!/usr/bin/env bash
set -Eeuo pipefail

# 0) В корень репо (если внутри)
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1) Python & venv
command -v $PY >/dev/null 2>&1 || PY="python3"
if [[ ! -d venv ]]; then
  echo "[i] creating venv..."
  $PY -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip wheel

# 2) Зависимости
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt
fi
if [[ -f requirements-dev.txt ]]; then
  pip install -r requirements-dev.txt
else
  # минимально необходимое для тестов
  pip install -U pytest
fi

# 3) Санити-импорты (падает, если критичные пакеты не установлены)
python - <<'PY'
import importlib, sys
for m in ("fastapi","sqlalchemy","httpx","pytest"):
    try:
        importlib.import_module(m)
    except Exception as e:
        print(f"[missing] {m}: {e}", file=sys.stderr)
        sys.exit(1)
print("[ok] deps sanity")
PY

# 4) Тестовая конфигурация
export PYTHONPATH="${PYTHONPATH:-.}:."
export ENVIRONMENT="${ENVIRONMENT:-test}"
export DOTENV_CONFIG="${DOTENV_CONFIG:-.env.test}"
if [[ -f .env.test ]]; then
  set -a; source .env.test; set +a
fi

# 5) База для тестов: предпочитаем временный Postgres, иначе SQLite
if [[ -z "${DATABASE_URL:-}" ]]; then
  if command -v docker >/dev/null 2>&1; then
    echo "[i] starting ephemeral postgres on :5433"
    docker rm -f pgtest >/dev/null 2>&1 || true
    if docker run -d --name pgtest -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=app \
      -p 5433:5432 postgres:15-alpine >/dev/null 2>&1; then
      export DATABASE_URL="postgresql+psycopg://test:test@localhost:5433/app"
      trap 'docker rm -f pgtest >/dev/null 2>&1 || true' EXIT
    else
      echo "[i] docker available but cannot run — falling back to SQLite"
      export DATABASE_URL="sqlite+aiosqlite:///:memory:"
    fi
  else
    echo "[i] docker not found — falling back to SQLite"
    export DATABASE_URL="sqlite+aiosqlite:///:memory:"
  fi
fi

# 6) Миграции базы данных (если есть скрипт)
if python -c "import importlib; importlib.import_module('nexus.api.db.migrate')" >/dev/null 2>&1; then
  echo "[i] running nexus.api.db.migrate"
  python -m nexus.api.db.migrate || echo "[i] migration script skipped/failed"
fi

# 7) Тесты
echo "[i] running pytest..."
pytest -q --maxfail=1 --disable-warnings

# 8) Коммит только если тесты зелёные
echo "[i] committing..."
# гарантируем, что мусор не уйдёт в репо
git add -A
git reset venv .venv >/dev/null 2>&1 || true
git reset '**/__pycache__/**' >/dev/null 2>&1 || true
# на всякий случай проверь, что .env* в .gitignore
git commit -m "ci(test): ensure venv, install deps, run tests — green locally" || {
  echo "[i] nothing to commit (working tree clean)"
}
