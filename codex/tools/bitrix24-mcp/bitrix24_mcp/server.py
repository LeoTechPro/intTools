import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from bitrix24_mcp.client import Bitrix24APIError, Bitrix24Client, redact, trim_json
from bitrix24_mcp.config import Config

logger = logging.getLogger("bitrix24_mcp.server")
mcp = FastMCP("Bitrix24 REST MCP Server")

_config: Config | None = None
_client: Bitrix24Client | None = None


def _load_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def _get_client() -> Bitrix24Client:
    global _client
    if _client is None:
        _client = Bitrix24Client(_load_config())
    return _client


def _health_payload(config: Config) -> dict[str, Any]:
    return {
        "ok": config.has_webhook_url,
        "has_webhook_url": config.has_webhook_url,
        "transport": config.transport,
        "port": config.port,
        "env_file": str(config.root_dir / ".env"),
    }


def _ok(data: Any, max_items: int = 25) -> dict[str, Any]:
    return {"ok": True, "data": trim_json(redact(data), max_items=max_items)}


def _error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, Bitrix24APIError):
        return {
            "ok": False,
            "error": exc.message,
            "status_code": exc.status_code,
            "detail": trim_json(redact(exc.detail), max_items=25),
        }
    return {"ok": False, "error": str(exc)}


async def _call(method: str, params: dict[str, Any] | None = None, max_items: int = 25) -> dict[str, Any]:
    data = await _get_client().call(method, params=params)
    return _ok(data, max_items=max_items)


@mcp.tool()
async def bitrix24_health() -> dict:
    """Show Bitrix24 REST MCP configuration status without exposing secrets."""
    return _health_payload(_load_config())


@mcp.tool()
async def bitrix24_profile(max_items: int = 25) -> dict:
    """Read current Bitrix24 webhook user profile."""
    try:
        return await _call("profile", max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_raw_read_call(method: str, params: dict = None, max_items: int = 25) -> dict:
    """Run an allowlisted read-only Bitrix24 REST call."""
    try:
        return await _call(method, params=params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_deal_fields(max_items: int = 25) -> dict:
    """Read Bitrix24 CRM deal field definitions."""
    try:
        return await _call("crm.deal.fields", max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_deal_get(deal_id: str, max_items: int = 25) -> dict:
    """Read one Bitrix24 CRM deal by id."""
    try:
        return await _call("crm.deal.get", {"id": str(deal_id).strip()}, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_deal_list(filter: dict = None, select: list[str] = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM deals with optional REST filter/select/order."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        return await _call("crm.deal.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_contact_fields(max_items: int = 25) -> dict:
    """Read Bitrix24 CRM contact field definitions."""
    try:
        return await _call("crm.contact.fields", max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_contact_get(contact_id: str, max_items: int = 25) -> dict:
    """Read one Bitrix24 CRM contact by id."""
    try:
        return await _call("crm.contact.get", {"id": str(contact_id).strip()}, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_contact_list(filter: dict = None, select: list[str] = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM contacts with optional REST filter/select/order."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        return await _call("crm.contact.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_company_get(company_id: str, max_items: int = 25) -> dict:
    """Read one Bitrix24 CRM company by id."""
    try:
        return await _call("crm.company.get", {"id": str(company_id).strip()}, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_company_list(filter: dict = None, select: list[str] = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM companies with optional REST filter/select/order."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        return await _call("crm.company.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_lead_get(lead_id: str, max_items: int = 25) -> dict:
    """Read one Bitrix24 CRM lead by id."""
    try:
        return await _call("crm.lead.get", {"id": str(lead_id).strip()}, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_lead_list(filter: dict = None, select: list[str] = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM leads with optional REST filter/select/order."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        return await _call("crm.lead.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_activity_list(filter: dict = None, select: list[str] = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM activities."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        return await _call("crm.activity.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_timeline_comment_list(filter: dict = None, select: list[str] = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM timeline comments."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        return await _call("crm.timeline.comment.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def bitrix24_status_list(filter: dict = None, order: dict = None, start: int = 0, max_items: int = 25) -> dict:
    """Read Bitrix24 CRM status dictionaries."""
    try:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if order:
            params["order"] = order
        return await _call("crm.status.list", params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Bitrix24 REST MCP server")
    parser.add_argument("--check", action="store_true", help="print safe config status and exit")
    parser.add_argument("--profile-smoke", action="store_true", help="call profile.json and exit")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(_health_payload(_load_config()), ensure_ascii=False, indent=2))
        return
    if args.profile_smoke:
        raise SystemExit(asyncio.run(_profile_smoke()))
    asyncio.run(_async_main())


async def _profile_smoke() -> int:
    try:
        data = await _get_client().call("profile")
        print(json.dumps(trim_json(redact(data), max_items=10), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_error(exc), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    finally:
        await _close_client()


async def _async_main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    config = _load_config()
    logger.info("Bitrix24 REST MCP configuration loaded: webhook_configured=%s", config.has_webhook_url)
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
