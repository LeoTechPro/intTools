#!/usr/bin/env python3
from __future__ import annotations

try:
    from .lockctl_core import main
except ImportError:
    from lockctl_core import main


if __name__ == "__main__":
    raise SystemExit(main())
