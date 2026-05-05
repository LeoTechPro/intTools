#!/usr/bin/env python3
try:
    from .coordctl_core import main
except ImportError:
    from coordctl_core import main


if __name__ == "__main__":
    raise SystemExit(main())
