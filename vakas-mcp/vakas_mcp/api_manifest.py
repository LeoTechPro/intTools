"""Load and validate the committed Vakas ingress API parity manifest."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path(__file__).with_name("api_manifest.json")


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("Vakas API manifest has no surfaces")
    identifiers = [row.get("id") for row in surfaces]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Vakas API manifest contains duplicate surface ids")
    for row in surfaces:
        fields = row.get("fields")
        if not isinstance(fields, list) or not fields or len(fields) != len(set(fields)):
            raise ValueError("Vakas API manifest contains invalid or duplicate fields")
        if row.get("transport_method") != "POST":
            raise ValueError("Vakas MCP transport is restricted to POST")
    return manifest


def tool_coverage() -> set[str]:
    return {
        tool
        for surface in load_manifest()["surfaces"]
        for tool in surface.get("tools", [])
    }
