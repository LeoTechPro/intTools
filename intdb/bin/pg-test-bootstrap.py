#!/usr/bin/env python3
from __future__ import annotations

import sys


if __name__ == "__main__":
    print(
        "Remote disposable test DB contour for /int/data is retired. "
        "Use `intdb local-test run --confirm-owner-control I_ACKNOWLEDGE_LOCAL_ONLY` instead.",
        file=sys.stderr,
    )
    raise SystemExit(2)
