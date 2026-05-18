from __future__ import annotations

import os
from typing import Any

import httpx


class TildaConfigError(RuntimeError):
    """Raised when required Tilda API configuration is missing."""


class TildaAPIError(RuntimeError):
    """Raised when Tilda API returns an error envelope or bad HTTP status."""

    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class TildaClient:
    BASE_URL = "https://api.tildacdn.info/v1"

    def __init__(self, public_key: str, secret_key: str, project_id: str | None = None) -> None:
        self.public_key = public_key
        self.secret_key = secret_key
        self.project_id = project_id

    @classmethod
    def from_env(cls) -> "TildaClient":
        public_key = os.getenv("TILDA_PUBLIC_KEY")
        secret_key = os.getenv("TILDA_SECRET_KEY")
        project_id = os.getenv("TILDA_PROJECT_ID") or None

        missing = [
            name
            for name, value in (
                ("TILDA_PUBLIC_KEY", public_key),
                ("TILDA_SECRET_KEY", secret_key),
            )
            if not value
        ]
        if missing:
            raise TildaConfigError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(public_key=public_key, secret_key=secret_key, project_id=project_id)

    async def request(self, method: str, **params: Any) -> dict[str, Any]:
        request_params = {
            "publickey": self.public_key,
            "secretkey": self.secret_key,
            **{key: value for key, value in params.items() if value is not None},
        }

        url = f"{self.BASE_URL}/{method}/"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=request_params)

        try:
            payload = response.json()
        except ValueError as exc:
            raise TildaAPIError(
                "Tilda API returned non-JSON response",
                status_code=response.status_code,
                detail=response.text[:500],
            ) from exc

        if response.status_code >= 400:
            raise TildaAPIError(
                "Tilda API HTTP error",
                status_code=response.status_code,
                detail=payload,
            )

        if payload.get("status") == "ERROR":
            raise TildaAPIError(
                str(payload.get("message") or "Tilda API error"),
                status_code=response.status_code,
                detail=payload,
            )

        return payload

    def require_project_id(self, projectid: str | None) -> str:
        resolved = projectid or self.project_id
        if not resolved:
            raise TildaConfigError("projectid is required or TILDA_PROJECT_ID must be configured")
        return resolved