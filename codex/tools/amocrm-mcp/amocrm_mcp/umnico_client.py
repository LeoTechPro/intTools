"""Async client for the Umnico Messaging API v1.3."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx
from aiolimiter import AsyncLimiter


class UmnicoAPIError(Exception):
    """Raised when Umnico returns a non-success response."""

    def __init__(self, status_code: int, message: str, detail: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f"[{status_code}] {message}: {detail}")


class UmnicoClient:
    """Rate-limited Umnico v1.3 client using an account JWT."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.umnico.com/v1.3",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("UMNICO_API_KEY is required")
        self._limiter = AsyncLimiter(max_rate=7, time_period=1)
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=30.0,
            headers={
                "Authorization": f"bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        await self._limiter.acquire()
        response = await self._client.request(method, path, params=params, json=json_data)

        for attempt in range(1, 4):
            if response.status_code != 429:
                break
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else min(2**attempt, 10) + random.random()
            await response.aclose()
            await asyncio.sleep(delay)
            await self._limiter.acquire()
            response = await self._client.request(method, path, params=params, json=json_data)

        if response.status_code >= 400:
            try:
                body = response.json()
                detail = body.get("message") or body.get("detail") or body.get("error") or str(body)
            except (ValueError, AttributeError):
                detail = response.text
            raise UmnicoAPIError(
                response.status_code,
                "Umnico API request failed",
                str(detail),
            )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()
