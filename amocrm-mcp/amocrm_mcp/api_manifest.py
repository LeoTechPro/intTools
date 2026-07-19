"""Committed public amoCRM endpoint registry."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    path = files("amocrm_mcp").joinpath("api_manifest.json")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def endpoint_index() -> dict[str, dict[str, Any]]:
    endpoints = load_manifest()["endpoints"]
    return {endpoint["id"]: endpoint for endpoint in endpoints}


def get_endpoint(endpoint_id: str) -> dict[str, Any]:
    try:
        return endpoint_index()[endpoint_id]
    except KeyError as exc:
        raise ValueError(f"Unknown amoCRM endpoint_id: {endpoint_id}") from exc
