from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from bitrix24_mcp.config import Config

SECRET_FIELD_PARTS = ("token", "secret", "password", "webhook")
READ_ONLY_METHOD_RE = re.compile(
    r"^(profile|user\.current|crm\.(deal|contact|company|lead|activity|status)\."
    r"(get|list|fields)|crm\.timeline\.comment\.list|crm\.item\.(get|list|fields))$"
)
MUTATING_METHOD_PARTS = (
    ".add",
    ".update",
    ".delete",
    ".set",
    ".bind",
    ".unbind",
    ".move",
    ".send",
    ".import",
    ".start",
    ".stop",
)

for _logger_name in ("httpx", "httpcore"):
    logging.getLogger(_logger_name).setLevel(logging.WARNING)


class Bitrix24APIError(Exception):
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
            result[key] = "***redacted***" if any(part in lowered for part in SECRET_FIELD_PARTS) else redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str) and "/rest/" in value:
        return re.sub(r"/rest/\d+/[^/]+/", "/rest/***/", value)
    return value


def trim_json(value: Any, max_items: int = 25, max_depth: int = 8) -> Any:
    if max_depth <= 0:
        return "..."
    if isinstance(value, dict):
        return {key: trim_json(item, max_items=max_items, max_depth=max_depth - 1) for key, item in value.items()}
    if isinstance(value, list):
        items = [trim_json(item, max_items=max_items, max_depth=max_depth - 1) for item in value[:max_items]]
        if len(value) > max_items:
            items.append({"_truncated": len(value) - max_items})
        return items
    return value


def normalize_method(method: str) -> str:
    clean = method.strip().removesuffix(".json")
    if not clean:
        raise Bitrix24APIError("method is required", 400)
    lowered = clean.lower()
    if any(part in lowered for part in MUTATING_METHOD_PARTS):
        raise Bitrix24APIError("Mutating Bitrix24 REST methods are blocked", 400, {"method": clean})
    if not READ_ONLY_METHOD_RE.match(lowered):
        raise Bitrix24APIError("Only allowlisted read-only Bitrix24 REST methods are allowed", 400, {"method": clean})
    return clean


class Bitrix24Client:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._client = httpx.AsyncClient(timeout=config.timeout, follow_redirects=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self.config.webhook_url:
            raise Bitrix24APIError("BITRIX_WEBHOOK_URL is not configured", 400)
        clean_method = normalize_method(method)
        response = await self._client.post(f"{self.config.webhook_url}{clean_method}.json", data=params or {})
        payload = self._parse_response(response)
        if response.status_code >= 400:
            raise Bitrix24APIError("Bitrix24 REST returned an HTTP error", response.status_code, payload)
        if isinstance(payload, dict) and payload.get("error"):
            raise Bitrix24APIError(str(payload.get("error_description") or payload.get("error")), response.status_code, payload)
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
