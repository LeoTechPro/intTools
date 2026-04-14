#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publish_entrypoint import run_bundle


if __name__ == "__main__":
    raise SystemExit(run_bundle(sys.argv[1:], Path(__file__).name))
