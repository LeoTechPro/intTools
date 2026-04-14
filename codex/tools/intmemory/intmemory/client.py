from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import IntMemoryConfig


class IntBrainClient:
    def __init__(self, config: IntMemoryConfig) -> None:
        self.config = config

    def store_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "context/store", payload=payload)

    def retrieve_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "context/retrieve", payload=payload)

    def context_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "context/pack", payload=payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.config.agent_id or not self.config.agent_key:
            raise RuntimeError("INTBRAIN_AGENT_ID and INTBRAIN_AGENT_KEY must be set")
        url = f"{self.config.api_base_url}/{path.lstrip('/')}"
        if params:
            query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
            if query:
                url = f"{url}?{query}"
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url=url, method=method, data=data)
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", "application/json")
        request.add_header("X-Agent-Id", self.config.agent_id)
        request.add_header("X-Agent-Key", self.config.agent_key)
        try:
            with urllib.request.urlopen(request, timeout=self.config.api_timeout_sec) as response:
                raw = response.read().decode("utf-8", errors="ignore")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="ignore")
            body = json.loads(raw) if raw else {}
            raise RuntimeError(json.dumps({"http_status": exc.code, "body": body}, ensure_ascii=False)) from exc
