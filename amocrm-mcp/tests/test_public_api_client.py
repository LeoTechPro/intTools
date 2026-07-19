from __future__ import annotations

import asyncio
import hashlib
import hmac
import os

import httpx

from amocrm_mcp.client import AmoClient


class FakeAuth:
    def get_access_token(self) -> str:
        return "access-token"

    async def refresh_token(self) -> None:
        return None


def test_public_rest_endpoint_renders_path_and_bearer() -> None:
    async def run() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v4/leads/42"
            assert request.headers["authorization"] == "Bearer access-token"
            return httpx.Response(200, json={"id": 42})

        client = AmoClient(FakeAuth(), "https://example.amocrm.ru")  # type: ignore[arg-type]
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.request_public_endpoint(
                {"path": "/api/v4/leads/{id}", "method": "GET", "host": "account", "surface": "rest", "auth": "oauth-bearer"},
                {"id": 42},
            )
            assert result == {"id": 42}
        finally:
            await client.close()

    asyncio.run(run())


def test_chats_endpoint_signs_exact_body() -> None:
    async def run() -> None:
        secret = "chat-secret"
        old = os.environ.get("AMO_CHAT_SECRET")
        os.environ["AMO_CHAT_SECRET"] = secret

        async def handler(request: httpx.Request) -> httpx.Response:
            body = await request.aread()
            expected = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
            assert request.headers["x-signature"] == expected
            assert request.url.path == "/v2/origin/custom/scope/chats"
            return httpx.Response(201, json={"ok": True})

        client = AmoClient(FakeAuth(), "https://example.amocrm.ru")  # type: ignore[arg-type]
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.request_public_endpoint(
                {"path": "/v2/origin/custom/{scope_id}/chats", "method": "POST", "host": "account", "surface": "chats", "auth": "hmac-sha1"},
                {"scope_id": "scope"},
                body={"conversation_id": "c1"},
            )
            assert result == {"ok": True}
        finally:
            await client.close()
            if old is None:
                os.environ.pop("AMO_CHAT_SECRET", None)
            else:
                os.environ["AMO_CHAT_SECRET"] = old

    asyncio.run(run())


def test_files_upload_supports_binary_and_content_range() -> None:
    async def run() -> None:
        old = os.environ.get("AMO_DRIVE_URL")
        os.environ["AMO_DRIVE_URL"] = "https://drive.example.test"

        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1.0/sessions/upload/token"
            assert request.headers["authorization"] == "Bearer access-token"
            assert request.headers["content-range"] == "bytes 0-2/3"
            assert await request.aread() == b"abc"
            return httpx.Response(204)

        client = AmoClient(FakeAuth(), "https://example.amocrm.ru")  # type: ignore[arg-type]
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.request_public_endpoint(
                {"path": "/v1.0/sessions/upload/{session_token}", "method": "POST", "host": "drive", "surface": "files", "auth": "oauth-bearer"},
                {"session_token": "token"},
                extra_headers={"Content-Range": "bytes 0-2/3"},
                content_base64="YWJj",
                content_type="application/octet-stream",
            )
            assert result == {}
        finally:
            await client.close()
            if old is None:
                os.environ.pop("AMO_DRIVE_URL", None)
            else:
                os.environ["AMO_DRIVE_URL"] = old

    asyncio.run(run())
