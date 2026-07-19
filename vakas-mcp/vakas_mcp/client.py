from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx


EVENT_FIELDS = {
    "registration": frozenset(
        {
            "email", "phone", "name", "utm_source", "utm_medium", "utm_campaign",
            "utm_content", "utm_term", "datetime", "vebinar_url",
        }
    ),
    "report": frozenset(
        {
            "email", "phone", "name", "dosmotrel_do_kontsa", "banner_click",
            "button_click", "data_webinara", "bil_minut", "web_room", "view",
            "viewTill", "city", "comments", "utm_source", "utm_medium",
            "utm_campaign", "utm_content", "utm_term",
        }
    ),
    "order": frozenset(
        {
            "email", "phone", "name", "number", "positions", "costMoney",
            "leftCostMoney", "payedMoney", "status", "paymentLink", "utm_source",
            "utm_medium", "utm_campaign", "utm_content", "utm_term",
        }
    ),
}
CONTACT_FIELDS = frozenset({"email", "phone"})
MAX_PAYLOAD_BYTES = 65536
MAX_VALUE_CHARS = 8192


class VakasError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def validate_destination(endpoint: str) -> None:
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise VakasError("invalid_destination", "Configured destination is invalid") from exc
    host = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme.lower() != "https":
        raise VakasError("invalid_destination", "Configured destination must use HTTPS")
    if not host or not (host == "vakas-tools.ru" or host.endswith(".vakas-tools.ru")):
        raise VakasError("destination_not_allowed", "Configured destination host is not allowlisted")
    if parsed.username or parsed.password or parsed.fragment:
        raise VakasError("invalid_destination", "Configured destination contains forbidden URL components")
    if port not in (None, 443):
        raise VakasError("destination_not_allowed", "Configured destination port is not allowlisted")
    if not parsed.path or parsed.path == "/":
        raise VakasError("invalid_destination", "Configured destination path is incomplete")


def normalize_payload(event_type: str, payload: dict[str, Any]) -> dict[str, str]:
    safe_event_type = event_type.strip().lower()
    allowed_fields = EVENT_FIELDS.get(safe_event_type)
    if allowed_fields is None:
        raise VakasError("unsupported_event_type", "Unsupported Vakas event type")
    if not isinstance(payload, dict) or not payload:
        raise VakasError("invalid_payload", "Payload must be a non-empty object")
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise VakasError(
            "unsupported_fields",
            "Payload contains fields outside the documented event allowlist: " + ", ".join(unknown_fields),
        )

    normalized: dict[str, str] = {}
    for field, value in payload.items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            rendered = "1" if value else "0"
        elif isinstance(value, (str, int, float)):
            rendered = str(value).strip()
        else:
            raise VakasError("invalid_field_type", f"Field {field} must be a scalar value")
        if len(rendered) > MAX_VALUE_CHARS:
            raise VakasError("field_too_large", f"Field {field} exceeds the size limit")
        if rendered:
            normalized[field] = rendered

    if not CONTACT_FIELDS.intersection(normalized):
        raise VakasError("missing_contact", "At least one contact field is required: email or phone")
    encoded_size = len(json.dumps(normalized, ensure_ascii=False).encode("utf-8"))
    if encoded_size > MAX_PAYLOAD_BYTES:
        raise VakasError("payload_too_large", "Payload exceeds the size limit")
    return normalized


def payload_summary(event_type: str, payload: dict[str, str]) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "fields": sorted(payload),
        "field_count": len(payload),
        "payload_bytes": len(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
        "personal_values_redacted": True,
    }


@dataclass(frozen=True)
class DispatchResult:
    status_code: int
    accepted: bool


class VakasClient:
    def __init__(self, *, timeout_seconds: float = 15.0, dedupe_ttl_seconds: int = 86400) -> None:
        self.timeout_seconds = timeout_seconds
        self.dedupe_ttl_seconds = dedupe_ttl_seconds
        self._dedupe: dict[str, float] = {}
        self._dedupe_lock = asyncio.Lock()

    def _dedupe_key(self, event_type: str, idempotency_key: str) -> str:
        return hashlib.sha256(f"{event_type}\0{idempotency_key}".encode()).hexdigest()

    async def _reserve(self, event_type: str, idempotency_key: str) -> str:
        now = time.monotonic()
        key = self._dedupe_key(event_type, idempotency_key)
        async with self._dedupe_lock:
            for item, expires_at in list(self._dedupe.items()):
                if expires_at <= now:
                    self._dedupe.pop(item, None)
            if key in self._dedupe:
                raise VakasError("duplicate_suppressed", "Duplicate idempotency key was suppressed", status_code=409)
            self._dedupe[key] = now + self.dedupe_ttl_seconds
        return key

    async def _release(self, key: str) -> None:
        async with self._dedupe_lock:
            self._dedupe.pop(key, None)

    async def dispatch(
        self,
        *,
        event_type: str,
        endpoint: str,
        payload: dict[str, str],
        idempotency_key: str,
    ) -> DispatchResult:
        validate_destination(endpoint)
        safe_key = idempotency_key.strip()
        if not safe_key or len(safe_key) > 200:
            raise VakasError("invalid_idempotency_key", "A bounded non-empty idempotency key is required")
        reservation = await self._reserve(event_type, safe_key)
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as http:
                response = await http.post(endpoint, data=payload)
        except httpx.HTTPError as exc:
            await self._release(reservation)
            raise VakasError("transport_error", "Vakas transport request failed", status_code=502) from exc
        accepted = 200 <= response.status_code < 300
        if not accepted:
            await self._release(reservation)
        return DispatchResult(status_code=response.status_code, accepted=accepted)
