from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from fastmcp import FastMCP

from tilda_mcp.client import TildaAPIError, TildaClient, TildaConfigError

logger = logging.getLogger("tilda_mcp.server")

mcp = FastMCP("Tilda MCP Server")


def _error_response(error: Exception) -> dict[str, Any]:
    if isinstance(error, TildaAPIError):
        return {
            "ok": False,
            "error": error.message,
            "status_code": error.status_code,
            "detail": error.detail,
        }
    return {"ok": False, "error": str(error)}


async def _call(method: str, **params: Any) -> dict[str, Any]:
    try:
        client = TildaClient.from_env()
        payload = await client.request(method, **params)
        return {"ok": True, **payload}
    except (TildaAPIError, TildaConfigError) as exc:
        return _error_response(exc)


@mcp.tool()
async def tilda_projects_list() -> dict[str, Any]:
    """List projects available to the configured Tilda API keys."""
    return await _call("getprojectslist")


@mcp.tool()
async def tilda_project_get(
    projectid: str | None = None,
    webconfig: Literal["htaccess", "nginx"] | None = None,
) -> dict[str, Any]:
    """Get project metadata, optionally with a web server config snippet."""
    try:
        client = TildaClient.from_env()
        resolved_projectid = client.require_project_id(projectid)
        payload = await client.request(
            "getprojectinfo",
            projectid=resolved_projectid,
            webconfig=webconfig,
        )
        return {"ok": True, **payload}
    except (TildaAPIError, TildaConfigError) as exc:
        return _error_response(exc)


@mcp.tool()
async def tilda_pages_list(projectid: str | None = None) -> dict[str, Any]:
    """List pages in a Tilda project."""
    try:
        client = TildaClient.from_env()
        resolved_projectid = client.require_project_id(projectid)
        payload = await client.request("getpageslist", projectid=resolved_projectid)
        return {"ok": True, **payload}
    except (TildaAPIError, TildaConfigError) as exc:
        return _error_response(exc)


@mcp.tool()
async def tilda_page_get(pageid: str) -> dict[str, Any]:
    """Get page metadata with body HTML and remote asset references."""
    return await _call("getpage", pageid=pageid)


@mcp.tool()
async def tilda_page_full_get(pageid: str) -> dict[str, Any]:
    """Get page metadata with full HTML and remote asset references."""
    return await _call("getpagefull", pageid=pageid)


@mcp.tool()
async def tilda_page_export_get(pageid: str) -> dict[str, Any]:
    """Get page body HTML and asset lists prepared for export."""
    return await _call("getpageexport", pageid=pageid)


@mcp.tool()
async def tilda_page_full_export_get(pageid: str) -> dict[str, Any]:
    """Get full page HTML and asset lists prepared for export."""
    return await _call("getpagefullexport", pageid=pageid)


async def _async_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("Tilda MCP server started")
    await mcp.run_stdio_async()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()