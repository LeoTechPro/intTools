from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = TOOLS_ROOT / "codex" / "bin" / "mcp-intdata-cli.py"


class ToolCallError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class InternalTool:
    profile: str
    name: str


CONTROL_TOOLS: dict[str, InternalTool] = {
    "routing_validate": InternalTool("intdata-control", "routing_validate"),
    "lockctl_status": InternalTool("intdata-control", "lockctl_status"),
}


class IntToolsAdapter:
    """Narrow adapter from ChatGPT Apps tools to allowlisted internal read-only tools."""

    def __init__(self, runtime: Any | None = None, *, default_owner_id: int | None = None) -> None:
        self._runtime = runtime
        self.default_owner_id = default_owner_id
        self._fetch_cache: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_env(cls) -> "IntToolsAdapter":
        owner_raw = os.getenv("INT_TOOLS_MCP_OWNER_ID", "").strip()
        owner_id = int(owner_raw) if owner_raw else None
        return cls(default_owner_id=owner_id)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search":
            return self.search(arguments)
        if name == "fetch":
            return self.fetch(arguments)
        if name in CONTROL_TOOLS:
            return self.control(name, arguments)
        raise ToolCallError("unknown_tool", f"unknown tool: {name}")

    def search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ToolCallError("invalid_request", "query is required")

        owner_id = _owner_id(arguments.get("owner_id"), self.default_owner_id)
        payload = {
            "owner_id": owner_id,
            "query": query,
            "limit": _bounded_int(arguments.get("limit"), default=10, minimum=1, maximum=25),
        }
        if arguments.get("days") is not None:
            payload["days"] = _bounded_int(arguments.get("days"), default=30, minimum=0, maximum=3650)
        if arguments.get("repo"):
            payload["repo"] = str(arguments["repo"]).strip()

        internal = self._call_internal("intbrain", "intbrain_memory_search", payload)
        if not internal.get("ok"):
            raise ToolCallError("internal_search_failed", "internal memory search failed", _public_result(internal))

        records = self._normalize_search_results(query, internal.get("data"))
        structured = {
            "query": query,
            "count": len(records),
            "results": records,
            "source": "intbrain.memory",
        }
        return _tool_result(
            structured,
            f"Found {len(records)} intData memory result(s).",
        )

    def fetch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        fetch_id = str(arguments.get("id") or "").strip()
        if not fetch_id:
            raise ToolCallError("invalid_request", "id is required")
        if not fetch_id.startswith("memory:"):
            raise ToolCallError("forbidden_fetch_id", "fetch accepts only safe ids returned by search")

        cached = self._fetch_cache.get(fetch_id)
        if cached is None:
            structured = {"id": fetch_id, "found": False, "item": None}
            return _tool_result(structured, f"No cached item found for {fetch_id}.")

        return _tool_result(
            {
                "id": fetch_id,
                "found": True,
                "item": cached["item"],
                "record": cached["record"],
            },
            f"Fetched {cached['record']['title']}.",
        )

    def control(self, public_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        internal_tool = CONTROL_TOOLS[public_name]
        safe_args = dict(arguments)
        if public_name == "routing_validate" and "json" not in safe_args:
            safe_args["json"] = True

        internal = self._call_internal(internal_tool.profile, internal_tool.name, safe_args)
        structured = {
            "tool": public_name,
            "ok": bool(internal.get("ok")),
            "result": _public_result(internal),
        }
        summary = f"{public_name} completed." if internal.get("ok") else f"{public_name} returned an error."
        return _tool_result(structured, summary, is_error=not bool(internal.get("ok")))

    def _normalize_search_results(self, query: str, data: Any) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for raw in _iter_candidate_items(data):
            stable = _stable_item_id(raw)
            if not stable:
                continue
            fetch_id = f"memory:{stable}"
            title = _first_text(raw, "title", "name", "thread_name", default="Memory item")
            text = _first_text(raw, "snippet", "text_content", "content", "text", "summary", "assistant_outcome", "user_goal", default="")
            record = {
                "id": stable,
                "fetch_id": fetch_id,
                "title": _truncate(title, 160),
                "snippet": _truncate(text, 500),
                "source": _first_text(raw, "source", default="intbrain.memory"),
                "type": _first_text(raw, "kind", "type", "chunk_kind", default="memory"),
            }
            self._fetch_cache[fetch_id] = {
                "record": record,
                "item": _public_item(raw),
                "query": query,
            }
            records.append(record)
        return records

    def _call_internal(self, profile: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        runtime = self._runtime or _load_runtime()
        result = runtime._call_tool(profile, name, arguments)  # noqa: SLF001
        if not isinstance(result, dict):
            raise ToolCallError("internal_result_error", f"internal tool returned non-object payload: {name}")
        return result


def _load_runtime() -> Any:
    spec = importlib.util.spec_from_file_location("intdata_chatgpt_mcp_runtime", RUNTIME_PATH)
    if spec is None or spec.loader is None:
        raise ToolCallError("runtime_load_failed", f"failed to load internal MCP runtime: {RUNTIME_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _owner_id(raw: Any, default_owner_id: int | None) -> int:
    value = raw if raw is not None else default_owner_id
    if value is None:
        raise ToolCallError("owner_id_required", "owner_id is required or INT_TOOLS_MCP_OWNER_ID must be set")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolCallError("invalid_owner_id", "owner_id must be an integer") from exc


def _bounded_int(raw: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError) as exc:
        raise ToolCallError("invalid_integer", f"value must be an integer between {minimum} and {maximum}") from exc
    return max(minimum, min(maximum, value))


def _iter_candidate_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("items", "results", "contexts", "memories", "matches"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for key in ("data", "context", "payload"):
        value = data.get(key)
        nested = _iter_candidate_items(value)
        if nested:
            return nested
    return []


def _stable_item_id(item: dict[str, Any]) -> str | None:
    for key in ("source_hash", "id", "memory_id", "context_id", "session_id"):
        value = item.get(key)
        if value:
            return str(value).strip()
    return None


def _first_text(item: dict[str, Any], *keys: str, default: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _truncate(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "id",
        "memory_id",
        "context_id",
        "session_id",
        "timestamp",
        "cwd",
        "repo",
        "title",
        "text_content",
        "content",
        "summary",
        "kind",
        "chunk_kind",
        "source",
        "source_path",
        "source_hash",
        "tags",
    }
    return {key: value for key, value in item.items() if key in allowed}


def _public_result(result: dict[str, Any]) -> dict[str, Any]:
    blocked = {"argv"}
    return {key: value for key, value in result.items() if key not in blocked}


def _tool_result(structured_content: dict[str, Any], text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
