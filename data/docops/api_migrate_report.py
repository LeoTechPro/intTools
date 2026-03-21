#!/usr/bin/env python3
"""Compare API inventory before and after migration."""

import json
from pathlib import Path


def main() -> None:
    inventory_path = Path(__file__).with_name("api_inventory.json")
    data = json.loads(inventory_path.read_text())
    before = {(p["method"], p["path"]) for p in data.get("before", [])}
    after = {(p["method"], p["path"]) for p in data.get("after", [])}

    old_before = {p for p in before if not p[1].startswith("/api/v1")}
    old_after = {p for p in after if not p[1].startswith("/api/v1")}
    migrated = len(old_before) - len(old_after)

    print(f"Total before: {len(before)}, after: {len(after)}")
    print(f"Old paths before: {len(old_before)}, after: {len(old_after)}")
    print(f"Migrated paths: {migrated}")
    if old_after:
        print("Remaining old paths:")
        for method, path in sorted(old_after):
            print(f"  {method} {path}")


if __name__ == "__main__":
    main()

