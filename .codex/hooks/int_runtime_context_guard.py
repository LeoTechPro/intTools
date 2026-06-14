#!/usr/bin/env python3
"""Compatibility wrapper for the shared /int Codex hook policy."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path("/int/.codex/hooks/lib")))

from int_hook_policy import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
