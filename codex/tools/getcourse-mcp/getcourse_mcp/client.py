from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from getcourse_mcp.config import Config

SECRET_FIELD_PARTS = ("key", "token", "secret", "password")
ALLOWED_PATH_PREFIX = "/pl/api/account/"
ALLOWED_WRITE_PATHS = {"/pl/api/users", "/pl/api/deals"}
TRANSIENT_ERROR_CODES = {903, 905}
EXPORT_NOT_READY_ERROR_CODES = {910}

for _logger_name in ("httpx", "httpcore"):
    logging.getLogger(_logger_name).setLevel(logging.WARNING)


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


def export_id_from_payload(payload: Any) -> str | None:
    """Extract GetCourse export id from known response envelope shapes."""
    if not isinstance(payload, dict):
        return None

    candidates = (
        payload.get("export_id"),
        (payload.get("info") or {}).get("export_id") if isinstance(payload.get("info"), dict) else None,
        (payload.get("result") or {}).get("export_id") if isinstance(payload.get("result"), dict) else None,
    )
    return next((str(value) for value in candidates if value), None)


def is_export_pending_payload(payload: Any) -> bool:
    """GetCourse can return success=false while an async export is being prepared."""
    return isinstance(payload, dict) and payload.get("success") is False and bool(export_id_from_payload(payload))


def error_code_from_payload(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None

    for key in ("error_code", "code"):
        value = payload.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass

    for key in ("error", "message"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            for token in value.replace(":", " ").replace(",", " ").split():
                if token.isdigit():
                    return int(token)

    for key in ("info", "result", "detail"):
        nested_code = error_code_from_payload(payload.get(key))
        if nested_code is not None:
            return nested_code

    return None


def is_transient_export_error_payload(payload: Any) -> bool:
    return error_code_from_payload(payload) in TRANSIENT_ERROR_CODES


def is_export_not_ready_payload(payload: Any) -> bool:
    return is_export_pending_payload(payload) or error_code_from_payload(payload) in EXPORT_NOT_READY_ERROR_CODES


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


def normalize_write_path(path: str) -> str:
    normalized = "/" + path.strip().lstrip("/")
    if normalized not in ALLOWED_WRITE_PATHS:
        raise GetCourseAPIError(
            "Only documented GetCourse import API write paths are allowed",
            400,
            {"path": normalized, "allowed": sorted(ALLOWED_WRITE_PATHS)},
        )
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

        if isinstance(payload, dict) and payload.get("success") is False and not is_export_pending_payload(payload):
            raise GetCourseAPIError(
                str(payload.get("error") or payload.get("message") or "GetCourse API error"),
                response.status_code,
                payload,
            )

        return payload

    async def post_import(self, path: str, action: str, params: dict[str, Any]) -> Any:
        if not self.config.account_domain:
            raise GetCourseAPIError("GETCOURSE_ACCOUNT_DOMAIN is not configured", 400)
        if not self.config.api_key:
            raise GetCourseAPIError("GetCourse API key is not configured", 401)

        clean_path = normalize_write_path(path)
        payload_json = json.dumps(params, ensure_ascii=False, separators=(",", ":"))
        encoded_params = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")

        response = await self._client.post(
            clean_path,
            data={
                "action": action,
                "key": self.config.api_key,
                "params": encoded_params,
            },
        )
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
