"""Load and query the committed Bitrix24 official API manifest."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path(__file__).with_name("api_manifest.json")


class ManifestError(ValueError):
    """Raised when a method is absent or is not a callable server method."""


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def entry_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in load_manifest()["entries"]:
        index[entry["id"].lower()] = entry
        index[entry["method"].lower()] = entry
    return index


def resolve_server_method(identifier: str) -> dict[str, Any]:
    clean = identifier.strip().removesuffix(".json")
    if not clean:
        raise ManifestError("method is required")
    entry = entry_index().get(clean.lower())
    if entry is None:
        raise ManifestError("method is absent from the committed official Bitrix24 manifest")
    if entry["kind"] != "server_method":
        raise ManifestError(f"manifest entry is not a callable server method: {entry['kind']}")
    return entry


def list_entries(
    *,
    query: str | None = None,
    kind: str | None = None,
    risk: str | None = None,
) -> list[dict[str, Any]]:
    rows = load_manifest()["entries"]
    if query:
        lowered = query.strip().lower()
        rows = [row for row in rows if lowered in row["method"].lower()]
    if kind:
        rows = [row for row in rows if row["kind"] == kind]
    if risk:
        rows = [row for row in rows if row["risk"] == risk]
    return rows
