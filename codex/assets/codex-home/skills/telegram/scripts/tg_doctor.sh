#!/usr/bin/env bash
set -euo pipefail

echo "[tg-doctor] env"
python3 --version

python3 - <<'PY'
import ctypes
import os
import runpy
import sys
from pathlib import Path

def mask_phone(phone: str) -> str:
    p = phone.strip()
    if not p:
        return ""
    if len(p) <= 4:
        return "***"
    return p[:2] + "***" + p[-2:]

conf_path = Path(os.path.expanduser("~/.config/tg/conf.py"))
print("[tg-doctor] config:", str(conf_path))
if not conf_path.exists():
    print("[tg-doctor] conf.py отсутствует. Запусти интерактивный tg один раз (через tmux), чтобы он создал конфиг.")
    sys.exit(2)

conf = runpy.run_path(str(conf_path))
phone = str(conf.get("PHONE", "") or "")
tdlib_path = str(conf.get("TDLIB_PATH", "") or "")

print("[tg-doctor] PHONE:", mask_phone(phone) if phone else "(missing)")
print("[tg-doctor] TDLIB_PATH:", tdlib_path if tdlib_path else "(not set)")

if tdlib_path:
    if not os.path.isfile(tdlib_path):
        print("[tg-doctor] ERROR: TDLIB_PATH указывает на несуществующий файл.")
        sys.exit(3)
    try:
        ctypes.CDLL(tdlib_path)
        print("[tg-doctor] tdlib load: OK")
    except OSError as e:
        print("[tg-doctor] tdlib load: FAIL:", e)
        sys.exit(4)
else:
    # Try default path used by python-telegram
    try:
        from telegram.tdjson import _get_tdjson_lib_path  # type: ignore
        p = _get_tdjson_lib_path()
        ctypes.CDLL(p)
        print("[tg-doctor] tdlib load (python-telegram default): OK:", p)
    except Exception as e:
        print("[tg-doctor] tdlib load (python-telegram default): FAIL:", e)
        print("[tg-doctor] Рекомендация: собрать TDLib под OpenSSL 3 и прописать TDLIB_PATH в conf.py.")
        sys.exit(5)

try:
    import tg as tg_pkg
    print("[tg-doctor] tg pkg:", tg_pkg.__version__)
except Exception as e:
    print("[tg-doctor] tg import: FAIL:", e)
    sys.exit(6)

try:
    import telegram as telegram_pkg
    v = getattr(telegram_pkg, "VERSION", None)
    print("[tg-doctor] python-telegram pkg:", v if v else "(unknown)")
except Exception as e:
    print("[tg-doctor] python-telegram import: FAIL:", e)
    sys.exit(7)

print("[tg-doctor] OK")
PY

