from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MCP_RUNTIME = REPO_ROOT / "codex" / "bin" / "mcp-intdata-cli.py"


class DispatchError(RuntimeError):
    pass


class ToolDispatcher:
    def __init__(self, runtime_path: Path = MCP_RUNTIME) -> None:
        self.runtime = _load_runtime(runtime_path)
        self.tool_to_profile = _build_tool_map(self.runtime.PROFILE_TOOLS)

    def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for profile, profile_tools in self.runtime.PROFILE_TOOLS.items():
            for tool in profile_tools:
                name = str(tool.get("name") or "")
                if _is_cabinet_tool(name):
                    continue
                tools.append({**tool, "profile": profile})
        return sorted(tools, key=lambda item: str(item.get("name")))

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        profile = self.tool_to_profile.get(name)
        if not profile:
            raise DispatchError(f"unknown tool: {name}")
        result = self.runtime._call_tool(profile, name, arguments)  # noqa: SLF001
        if not isinstance(result, dict):
            raise DispatchError(f"tool returned non-object payload: {name}")
        return result


class StaticDispatcher:
    def __init__(self, result: dict[str, Any] | None = None) -> None:
        self.result = result or {"ok": True, "data": {"static": True}}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "intbrain_context_pack", "description": "test", "inputSchema": {"type": "object"}}]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        return self.result


def _load_runtime(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("intdata_mcp_runtime", path)
    if spec is None or spec.loader is None:
        raise DispatchError(f"failed to load MCP runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_tool_map(profile_tools: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    tool_map: dict[str, str] = {}
    for profile, tools in profile_tools.items():
        for tool in tools:
            name = str(tool.get("name") or "")
            if _is_cabinet_tool(name):
                continue
            if name and name not in tool_map:
                tool_map[name] = profile
    return tool_map


def _is_cabinet_tool(name: str) -> bool:
    return name.startswith("cabinet_") or name.startswith("cabinet.") or "_cabinet_" in name or name.endswith("_cabinet")
