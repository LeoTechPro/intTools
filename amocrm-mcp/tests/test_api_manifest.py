from __future__ import annotations

import asyncio

from amocrm_mcp.api_manifest import endpoint_index, load_manifest
from amocrm_mcp.tools.public_api import PublicApiCallInput, amocrm_api_call


def test_manifest_is_unique_and_covers_every_backend_surface() -> None:
    manifest = load_manifest()
    endpoints = manifest["endpoints"]
    assert len(endpoints) >= 200
    assert len({row["id"] for row in endpoints}) == len(endpoints)
    assert len({(row["surface"], row["method"], row["path"]) for row in endpoints}) == len(endpoints)
    assert {row["surface"] for row in endpoints} == {"rest", "webhooks", "chats", "files", "telephony"}
    assert all(row["source"].startswith("https://www.amocrm.ru/developers/") for row in endpoints)
    assert all(row["path"].count("{") == row["path"].count("}") for row in endpoints)


def test_manifest_contains_high_risk_and_special_host_operations() -> None:
    rows = endpoint_index().values()
    signatures = {(row["surface"], row["method"], row["path"]) for row in rows}
    assert ("rest", "DELETE", "/api/v4/leads/pipelines/{id}") in signatures
    assert ("webhooks", "POST", "/api/v4/webhooks") in signatures
    assert ("chats", "POST", "/v2/origin/custom/{channel.id}/connect") in signatures
    assert ("files", "POST", "/v1.0/sessions") in signatures
    assert ("telephony", "POST", "/api/v2/events/") in signatures
    assert all(row["host"] == "drive" for row in rows if row["path"].startswith("/v1.0/"))
    assert all(row["auth"] == "hmac-sha1" for row in rows if row["surface"] == "chats")


def test_browser_only_api_is_explicitly_excluded() -> None:
    exclusions = load_manifest()["excluded_surfaces"]
    assert any(row["name"] == "notifications-ui" for row in exclusions)


def test_unknown_endpoint_fails_as_a_tool_error_envelope() -> None:
    result = asyncio.run(amocrm_api_call(PublicApiCallInput(endpoint_id="not-in-manifest")))
    assert result["status_code"] == 400
