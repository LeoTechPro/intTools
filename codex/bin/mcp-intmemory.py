#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys


ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
MODULE_ROOT = ROOT_DIR / "tools" / "intmemory"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from intmemory.mcp_server import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
