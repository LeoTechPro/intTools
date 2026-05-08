import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from getcourse_mcp.client import GetCourseAPIError, GetCourseClient, redact, trim_json
from getcourse_mcp.config import Config

logger = logging.getLogger("getcourse_mcp.server")

EXPORT_ENDPOINTS = {
    "users": "/pl/api/account/users",
    "orders": "/pl/api/account/deals",
    "deals": "/pl/api/account/deals",
    "payments": "/pl/api/account/payments",
}

mcp = FastMCP("GetCourse MCP Server")

_config: Config | None = None
_client: GetCourseClient | None = None


def _quiet_transport_logs() -> None:
    for logger_name in ("httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _load_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def _get_client() -> GetCourseClient:
    global _client
    if _client is None:
        _client = GetCourseClient(_load_config())
    return _client


def _health_payload(config: Config) -> dict[str, Any]:
    return {
        "ok": bool(config.account_domain),
        "account_domain": config.account_domain or None,
        "api_base_url": config.api_base_url if config.account_domain else None,
        "has_api_key": config.has_api_key,
        "transport": config.transport,
        "port": config.port,
        "env_file": str(config.root_dir / ".env"),
    }


def _ok(data: Any, max_items: int = 25) -> dict[str, Any]:
    return {"ok": True, "data": trim_json(redact(data), max_items=max_items)}


def _error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, GetCourseAPIError):
        return {
            "ok": False,
            "error": exc.message,
            "status_code": exc.status_code,
            "detail": trim_json(redact(exc.detail), max_items=25),
        }

    return {"ok": False, "error": str(exc)}


@mcp.tool()
async def getcourse_health() -> dict:
    """Show GetCourse MCP configuration status without exposing secrets."""
    return _health_payload(_load_config())


@mcp.tool()
async def getcourse_groups_list(max_items: int = 50) -> dict:
    """List GetCourse groups using a read-only account API request."""
    try:
        data = await _get_client().get("/pl/api/account/groups")
        return _ok(data, max_items=max_items)
    except Exception as exc:  # noqa: BLE001 - returned to MCP caller as data
        return _error(exc)


@mcp.tool()
async def getcourse_start_export(
    dataset: str,
    params: dict = None,
    max_items: int = 25,
) -> dict:
    """Start a GetCourse export for users, orders/deals, or payments."""
    try:
        endpoint = EXPORT_ENDPOINTS.get(dataset.strip().lower())
        if endpoint is None:
            raise GetCourseAPIError(
                "Unsupported export dataset",
                400,
                {"dataset": dataset, "allowed": sorted(EXPORT_ENDPOINTS)},
            )

        data = await _get_client().get(endpoint, params=params)
        return _ok(data, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_export_get(export_id: str, max_items: int = 25) -> dict:
    """Read a GetCourse export result by export id."""
    try:
        safe_export_id = export_id.strip()
        if not safe_export_id:
            raise GetCourseAPIError("export_id is required", 400)

        data = await _get_client().get(f"/pl/api/account/exports/{safe_export_id}")
        return _ok(data, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_group_users_export(group_id: str, max_items: int = 25) -> dict:
    """Start a GetCourse export of users from a group."""
    try:
        safe_group_id = group_id.strip()
        if not safe_group_id:
            raise GetCourseAPIError("group_id is required", 400)

        data = await _get_client().get(f"/pl/api/account/groups/{safe_group_id}/users")
        return _ok(data, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_raw_get(
    path: str,
    params: dict = None,
    max_items: int = 25,
) -> dict:
    """Run a safe read-only GET request under /pl/api/account/..."""
    try:
        data = await _get_client().get(path, params=params)
        return _ok(data, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


def main() -> None:
    _quiet_transport_logs()

    parser = argparse.ArgumentParser(description="Read-only GetCourse MCP server")
    parser.add_argument("--check", action="store_true", help="print safe config status and exit")
    parser.add_argument("--groups-smoke", action="store_true", help="call the groups endpoint and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps(_health_payload(_load_config()), ensure_ascii=False, indent=2))
        return

    if args.groups_smoke:
        raise SystemExit(asyncio.run(_groups_smoke()))

    asyncio.run(_async_main())


async def _groups_smoke() -> int:
    try:
        data = await _get_client().get("/pl/api/account/groups")
        print(json.dumps(trim_json(redact(data), max_items=10), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_error(exc), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    finally:
        await _close_client()


async def _async_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    _quiet_transport_logs()

    config = _load_config()
    logger.info(
        "GetCourse MCP configuration loaded: domain=%s key_configured=%s",
        config.account_domain or "<missing>",
        config.has_api_key,
    )

    try:
        if config.transport == "sse":
            await mcp.run_sse_async(host="0.0.0.0", port=config.port)
        elif config.transport in {"streamable-http", "http"}:
            await mcp.run_streamable_http_async(host="0.0.0.0", port=config.port)
        else:
            await mcp.run_stdio_async()
    finally:
        await _close_client()


async def _close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
