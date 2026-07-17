from __future__ import annotations

import asyncio

import httpx

from amocrm_mcp.umnico_client import UmnicoAPIError, UmnicoClient
from amocrm_mcp.tools.umnico import SendFirstInput, umnico_send_first


def test_umnico_client_sends_bearer_and_returns_json() -> None:
    async def run() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["authorization"] == "bearer test-token"
            assert request.url.path == "/v1.3/account/me"
            return httpx.Response(200, json={"account": {"id": 112775, "status": "active"}})

        client = UmnicoClient("test-token", transport=httpx.MockTransport(handler))
        try:
            data = await client.request("GET", "/account/me")
            assert data["account"]["status"] == "active"
        finally:
            await client.close()

    asyncio.run(run())


def test_umnico_client_maps_api_error() -> None:
    async def run() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"message": "forbidden"})

        client = UmnicoClient("test-token", transport=httpx.MockTransport(handler))
        try:
            try:
                await client.request("GET", "/integrations")
            except UmnicoAPIError as exc:
                assert exc.status_code == 403
                assert exc.detail == "forbidden"
            else:
                raise AssertionError("UmnicoAPIError was not raised")
        finally:
            await client.close()

    asyncio.run(run())


def test_send_first_requires_explicit_confirmation() -> None:
    result = asyncio.run(
        umnico_send_first(
            SendFirstInput(
                destination="+70000000000",
                sa_id=1,
                text="guard-smoke",
                confirm_send=False,
            )
        )
    )
    assert result["status_code"] == 409
