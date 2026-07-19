from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import random
import re
from typing import Any
from urllib.parse import quote

import httpx
from aiolimiter import AsyncLimiter

from amocrm_mcp.auth import AuthManager, RefreshTokenExpiredError

logger = logging.getLogger("amocrm_mcp.client")

MAX_429_RETRIES = 5
RATE_LIMIT_MAX_RATE = 7
RATE_LIMIT_TIME_PERIOD = 1

HTTP_STATUS_MESSAGES: dict[int, str] = {
    400: "Bad request. Check the request parameters and payload format.",
    401: "Authentication failed. Token may be invalid or expired.",
    403: "Access forbidden. The integration lacks required permissions for this operation.",
    404: "Resource not found. Verify the entity ID or endpoint path.",
    422: "Unprocessable entity. The request payload contains invalid field values.",
    429: "Rate limit exceeded. Too many requests to the amoCRM API.",
    500: "amoCRM internal server error. Retry the request later.",
    502: "Bad gateway. amoCRM upstream is temporarily unavailable.",
    504: "Gateway timeout. amoCRM did not respond in time.",
}


class AmoAPIError(Exception):
    """Raised on non-retryable amoCRM API errors."""

    def __init__(self, status_code: int, message: str, detail: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f"[{status_code}] {message}: {detail}")


class AmoClient:
    """Async amoCRM API client with rate limiting, HAL normalization, and error mapping.

    Uses RateLimitedTransport for all requests, providing:
    - 7 req/s throttling with queued backpressure (FR-5)
    - Transparent 401 refresh/retry (FR-2)
    - 429 exponential backoff (FR-6)
    """

    def __init__(self, auth: AuthManager, base_url: str) -> None:
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._limiter = AsyncLimiter(max_rate=RATE_LIMIT_MAX_RATE, time_period=RATE_LIMIT_TIME_PERIOD)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        """Execute an API request, returning normalized response data.

        Raises AmoAPIError on non-success status codes.
        Raises RefreshTokenExpiredError when the refresh token is expired.
        """
        response = await self._send_request(
            method=method,
            path=path,
            params=params,
            json=json_data,
        )

        if response.status_code == 204:
            return {}

        if response.status_code >= 400:
            detail = ""
            try:
                body = response.json()
                detail = body.get("detail", body.get("title", str(body)))
            except (ValueError, KeyError):
                detail = response.text
            status_msg = HTTP_STATUS_MESSAGES.get(
                response.status_code,
                f"Unexpected error (HTTP {response.status_code}).",
            )
            raise AmoAPIError(
                status_code=response.status_code,
                message=status_msg,
                detail=detail,
            )

        if response.status_code == 200 or response.status_code == 202:
            data = response.json()
            return normalize_response(data)

        return response.json()

    async def request_public_endpoint(
        self,
        endpoint: dict[str, Any],
        path_parameters: dict[str, str | int],
        params: dict | None = None,
        extra_headers: dict[str, str] | None = None,
        body: Any | None = None,
        content_base64: str | None = None,
        content_type: str | None = None,
    ) -> Any:
        """Execute one committed manifest endpoint on its documented host/auth surface."""
        path = endpoint["path"]
        for placeholder in re.findall(r"\{([^{}]+)\}", path):
            key = placeholder.split(":", 1)[0]
            if placeholder in path_parameters:
                value = path_parameters[placeholder]
            elif key in path_parameters:
                value = path_parameters[key]
            else:
                raise AmoAPIError(400, "Missing path parameter", key)
            path = path.replace("{" + placeholder + "}", quote(str(value), safe=""))
        if "{" in path or "}" in path:
            raise AmoAPIError(400, "Unresolved path parameter", path)

        raw_content: bytes | None = None
        if content_base64 is not None:
            try:
                raw_content = base64.b64decode(content_base64, validate=True)
            except ValueError as exc:
                raise AmoAPIError(400, "Invalid base64 content", str(exc)) from exc

        host = endpoint["host"]
        if host == "drive":
            base_url = await self._resolve_drive_url()
        elif endpoint["surface"] == "chats":
            base_url = os.environ.get("AMO_CHAT_BASE_URL", "https://amojo.amocrm.ru").rstrip("/")
        else:
            base_url = self._base_url
        url = base_url + "/" + path.lstrip("/")

        reserved_headers = {"authorization", "host", "x-signature"}
        headers: dict[str, str] = {
            key: value
            for key, value in (extra_headers or {}).items()
            if key.lower() not in reserved_headers
        }
        if content_type:
            headers["Content-Type"] = content_type
        elif raw_content is not None:
            headers["Content-Type"] = "application/octet-stream"

        json_data = body if raw_content is None else None
        if endpoint["auth"] == "hmac-sha1":
            secret = os.environ.get("AMO_CHAT_SECRET", "").strip()
            if not secret:
                raise AmoAPIError(503, "Chats API is not configured", "Set AMO_CHAT_SECRET in the runtime secret store")
            if raw_content is None:
                raw_content = (
                    json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    if body is not None
                    else b""
                )
                json_data = None
                headers.setdefault("Content-Type", "application/json")
            headers["X-Signature"] = hmac.new(secret.encode("utf-8"), raw_content, hashlib.sha1).hexdigest()
        else:
            headers["Authorization"] = f"Bearer {self._auth.get_access_token()}"

        response = await self._send_public_request(
            method=endpoint["method"],
            url=url,
            params=params,
            json_data=json_data,
            content=raw_content,
            headers=headers,
            bearer=endpoint["auth"] == "oauth-bearer",
        )
        return self._decode_public_response(response)

    async def _resolve_drive_url(self) -> str:
        configured = os.environ.get("AMO_DRIVE_URL", "").strip()
        if configured:
            return configured.rstrip("/")
        account = await self.request("GET", "/api/v4/account", params={"with": "drive_url"})
        drive_url = account.get("drive_url") if isinstance(account, dict) else None
        if not drive_url:
            raise AmoAPIError(503, "Files API drive host is unavailable", "Set AMO_DRIVE_URL or grant account drive_url access")
        return str(drive_url).rstrip("/")

    async def _send_public_request(
        self,
        method: str,
        url: str,
        params: dict | None,
        json_data: Any | None,
        content: bytes | None,
        headers: dict[str, str],
        bearer: bool,
    ) -> httpx.Response:
        import asyncio

        for attempt in range(MAX_429_RETRIES + 1):
            await self._limiter.acquire()
            response = await self._client.request(
                method,
                url,
                params=params,
                json=json_data,
                content=content,
                headers=headers,
            )
            if response.status_code == 401 and bearer and attempt == 0:
                await response.aclose()
                await self._auth.refresh_token()
                headers["Authorization"] = f"Bearer {self._auth.get_access_token()}"
                continue
            if response.status_code != 429 or attempt == MAX_429_RETRIES:
                return response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else min(2 ** (attempt + 1), 60) + random.uniform(0, 1)
            await response.aclose()
            await asyncio.sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _decode_public_response(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            try:
                error_body = response.json()
                detail = error_body.get("detail", error_body.get("title", str(error_body)))
            except (ValueError, AttributeError):
                detail = response.text
            raise AmoAPIError(
                response.status_code,
                HTTP_STATUS_MESSAGES.get(response.status_code, f"Unexpected error (HTTP {response.status_code})."),
                detail,
            )
        if response.status_code == 204 or not response.content:
            return {}
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" in content_type:
            return normalize_response(response.json())
        if content_type.startswith("text/"):
            return {"text": response.text, "content_type": content_type}
        return {
            "content_base64": base64.b64encode(response.content).decode("ascii"),
            "content_type": content_type or "application/octet-stream",
        }

    async def _send_request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._auth.get_access_token()}"}
        await self._limiter.acquire()
        response = await self._client.request(method, path, params=params, json=json, headers=headers)

        if response.status_code == 401:
            logger.info("Received 401, attempting token refresh")
            await response.aclose()
            await self._auth.refresh_token()
            headers["Authorization"] = f"Bearer {self._auth.get_access_token()}"
            await self._limiter.acquire()
            response = await self._client.request(method, path, params=params, json=json, headers=headers)

        if response.status_code == 429:
            response = await self._handle_429(method, path, params, json, headers, response)

        return response

    async def _handle_429(
        self,
        method: str,
        path: str,
        params: dict | None,
        json: dict | None,
        headers: dict[str, str],
        response: httpx.Response,
    ) -> httpx.Response:
        import asyncio

        for attempt in range(1, MAX_429_RETRIES + 1):
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                delay = float(retry_after)
            else:
                delay = min(2 ** attempt, 60) + random.uniform(0, 1)

            logger.warning("429 backoff attempt %d/%d, waiting %.1fs", attempt, MAX_429_RETRIES, delay)
            await response.aclose()
            await asyncio.sleep(delay)
            await self._limiter.acquire()
            response = await self._client.request(
                method,
                path,
                params=params,
                json=json,
                headers=headers,
            )
            if response.status_code != 429:
                return response

        return response

    async def __aenter__(self) -> AmoClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def normalize_response(data: Any) -> Any:
    """Strip _links and flatten _embedded from amoCRM HAL+JSON responses (FR-7, ADR-003).

    Recursively processes dicts and lists. Merges _embedded children into
    the parent dict. Removes _links at every level.
    """
    if isinstance(data, list):
        return [normalize_response(item) for item in data]

    if not isinstance(data, dict):
        return data

    result: dict[str, Any] = {}

    for key, value in data.items():
        if key == "_links":
            continue
        if key == "_embedded":
            if isinstance(value, dict):
                for embed_key, embed_value in value.items():
                    result[embed_key] = normalize_response(embed_value)
            continue
        result[key] = normalize_response(value)

    return result


def build_filters(filters: dict) -> dict:
    """Convert flat filter dict to amoCRM bracket notation (FR-26).

    Conversion rules:
    - key ending with '_from' -> filter[base][from]
    - key ending with '_to'   -> filter[base][to]
    - list value              -> filter[key][]
    - scalar value            -> filter[key][]  (wrapped in list)
    """
    result: dict[str, Any] = {}

    for key, value in filters.items():
        if value is None:
            continue

        if key.endswith("_from"):
            base = key[: -len("_from")]
            result[f"filter[{base}][from]"] = value
        elif key.endswith("_to"):
            base = key[: -len("_to")]
            result[f"filter[{base}][to]"] = value
        elif isinstance(value, list):
            result[f"filter[{key}][]"] = value
        else:
            result[f"filter[{key}][]"] = [value]

    return result


def success_response(data: Any, pagination: dict | None = None) -> dict:
    """Build a standardized success envelope (FR-23).

    Returns {data, pagination} for list operations or {data} for single entities.
    """
    envelope: dict[str, Any] = {"data": data}
    if pagination is not None:
        envelope["pagination"] = pagination
    return envelope


def error_response(error: str, status_code: int, detail: str) -> dict:
    """Build a standardized error envelope (FR-23, FR-28)."""
    return {
        "error": error,
        "status_code": status_code,
        "detail": detail,
    }
