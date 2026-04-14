#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
MODULE_ROOT = ROOT_DIR / "tools" / "intmemory"
sys.path = [item for item in sys.path if pathlib.Path(item or ".").resolve() != SCRIPT_DIR]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from intmemory.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
