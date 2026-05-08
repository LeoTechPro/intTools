from __future__ import annotations

from typing import Any

import httpx

from getcourse_mcp.config import Config

SECRET_FIELD_PARTS = ("key", "token", "secret", "password")
ALLOWED_PATH_PREFIX = "/pl/api/account/"


class GetCourseAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = redact(detail)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SECRET_FIELD_PARTS):
                result[key] = "***redacted***"
            else:
                result[key] = redact(item)
        return result

    if isinstance(value, list):
        return [redact(item) for item in value]

    return value


def trim_json(value: Any, max_items: int = 25, max_depth: int = 8) -> Any:
    if max_depth <= 0:
        return "..."

    if isinstance(value, dict):
        return {
            key: trim_json(item, max_items=max_items, max_depth=max_depth - 1)
            for key, item in value.items()
        }

    if isinstance(value, list):
        items = [
            trim_json(item, max_items=max_items, max_depth=max_depth - 1)
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            items.append({"_truncated": len(value) - max_items})
        return items

    return value


def normalize_path(path: str) -> str:
    normalized = "/" + path.strip().lstrip("/")
    if not normalized.startswith(ALLOWED_PATH_PREFIX):
        raise GetCourseAPIError(
            "Only read-only GetCourse account API paths are allowed",
            400,
            {"path": normalized, "allowed_prefix": ALLOWED_PATH_PREFIX},
        )
    if any(part in normalized for part in ("..", "//")):
        raise GetCourseAPIError("Unsafe API path", 400, {"path": normalized})
    return normalized


class GetCourseClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.api_base_url if config.account_domain else "https://example.invalid",
            timeout=config.timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.config.account_domain:
            raise GetCourseAPIError("GETCOURSE_ACCOUNT_DOMAIN is not configured", 400)
        if not self.config.api_key:
            raise GetCourseAPIError("GetCourse API key is not configured", 401)

        clean_path = normalize_path(path)
        query = {key: value for key, value in (params or {}).items() if value is not None}
        query["key"] = self.config.api_key

        response = await self._client.get(clean_path, params=query)
        payload = self._parse_response(response)

        if response.status_code >= 400:
            raise GetCourseAPIError(
                "GetCourse API returned an HTTP error",
                response.status_code,
                payload,
            )

        if isinstance(payload, dict) and payload.get("success") is False:
            raise GetCourseAPIError(
                str(payload.get("error") or payload.get("message") or "GetCourse API error"),
                response.status_code,
                payload,
            )

        return payload

    @staticmethod
    def _parse_response(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            text = response.text
            if len(text) > 4000:
                text = text[:4000] + "...[truncated]"
            return {"raw_text": text}
