import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from getcourse_mcp.client import (
    GetCourseAPIError,
    GetCourseClient,
    error_code_from_payload,
    export_id_from_payload,
    is_export_not_ready_payload,
    is_export_pending_payload,
    is_transient_export_error_payload,
    redact,
    trim_json,
)
from getcourse_mcp.config import Config

logger = logging.getLogger("getcourse_mcp.server")

EXPORT_ENDPOINTS = {
    "users": "/pl/api/account/users",
    "orders": "/pl/api/account/deals",
    "deals": "/pl/api/account/deals",
    "payments": "/pl/api/account/payments",
}
WRITE_ENDPOINTS = {
    "users": "/pl/api/users",
    "deals": "/pl/api/deals",
}
MAX_POLL_ATTEMPTS = 10
MAX_POLL_INTERVAL_SECONDS = 10.0

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
        detail = trim_json(redact(exc.detail), max_items=25)
        result: dict[str, Any] = {
            "ok": False,
            "error": exc.message,
            "status_code": exc.status_code,
            "detail": detail,
        }
        if is_transient_export_error_payload(exc.detail):
            result["transient"] = True
            result["retry_hint"] = (
                "GetCourse Export API is busy or rate-limited. It is single-threaded per account "
                "and limited to 100 export requests per 2 hours; retry later without parallel export jobs."
            )
            error_code = error_code_from_payload(exc.detail)
            if error_code is not None:
                result["error_code"] = error_code
        return result

    return {"ok": False, "error": str(exc)}


def _bounded_int(value: int, *, minimum: int, maximum: int, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise GetCourseAPIError(f"{name} must be an integer", 400, {name: value}) from exc
    return max(minimum, min(maximum, parsed))


def _bounded_float(value: float, *, minimum: float, maximum: float, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise GetCourseAPIError(f"{name} must be a number", 400, {name: value}) from exc
    return max(minimum, min(maximum, parsed))


def _add_range(params: dict[str, Any], field: str, from_value: str | None, to_value: str | None) -> None:
    if from_value:
        params[f"{field}[from]"] = from_value
    if to_value:
        params[f"{field}[to]"] = to_value


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value not in (None, "")}


def _require_filter(params: dict[str, Any], dataset: str) -> None:
    if not params:
        raise GetCourseAPIError(
            "At least one export filter is required",
            400,
            {
                "dataset": dataset,
                "reason": "Avoid accidental full-account exports from MCP.",
            },
        )


def _build_user_filters(
    *,
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    added_from: str | None = None,
    added_to: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"status": status}
    _add_range(params, "created_at", created_from, created_to)
    _add_range(params, "added_at", added_from, added_to)
    return _compact_params(params)


def _build_deal_filters(
    *,
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    payed_from: str | None = None,
    payed_to: str | None = None,
    finished_from: str | None = None,
    finished_to: str | None = None,
    status_changed_from: str | None = None,
    status_changed_to: str | None = None,
    user_id: str | None = None,
    user_in_group: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "status": status,
        "user_id": user_id,
        "user_in_group": user_in_group,
    }
    _add_range(params, "created_at", created_from, created_to)
    _add_range(params, "payed_at", payed_from, payed_to)
    _add_range(params, "finished_at", finished_from, finished_to)
    _add_range(params, "status_changed_at", status_changed_from, status_changed_to)
    return _compact_params(params)


def _build_payment_filters(
    *,
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    status_changed_from: str | None = None,
    status_changed_to: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"status": status}
    _add_range(params, "created_at", created_from, created_to)
    _add_range(params, "status_changed_at", status_changed_from, status_changed_to)
    return _compact_params(params)


def _require_confirm_write(confirm_write: bool) -> None:
    if confirm_write is not True:
        raise GetCourseAPIError(
            "confirm_write=True is required for GetCourse Import API mutations",
            400,
            {
                "safety": "This tool can create or update GetCourse data through the documented Import API.",
            },
        )


async def _post_import(
    *,
    resource: str,
    action: str,
    params: dict[str, Any],
    confirm_write: bool,
    max_items: int = 25,
) -> dict[str, Any]:
    _require_confirm_write(confirm_write)
    endpoint = WRITE_ENDPOINTS.get(resource)
    if endpoint is None:
        raise GetCourseAPIError(
            "Unsupported write resource",
            400,
            {"resource": resource, "allowed": sorted(WRITE_ENDPOINTS)},
        )
    if not params:
        raise GetCourseAPIError("params are required", 400)

    data = await _get_client().post_import(endpoint, action=action, params=params)
    return _ok(data, max_items=max_items)


async def _start_export(dataset: str, params: dict[str, Any] | None = None, max_items: int = 25) -> dict[str, Any]:
    endpoint = EXPORT_ENDPOINTS.get(dataset.strip().lower())
    if endpoint is None:
        raise GetCourseAPIError(
            "Unsupported export dataset",
            400,
            {"dataset": dataset, "allowed": sorted(EXPORT_ENDPOINTS)},
        )

    data = await _get_client().get(endpoint, params=params)
    result = _ok(data, max_items=max_items)
    export_id = export_id_from_payload(data)
    if export_id:
        result["export_id"] = export_id
        result["pending"] = True
    return result


async def _read_export(export_id: str, max_items: int = 25) -> dict[str, Any]:
    safe_export_id = export_id.strip()
    if not safe_export_id:
        raise GetCourseAPIError("export_id is required", 400)

    try:
        data = await _get_client().get(f"/pl/api/account/exports/{safe_export_id}")
    except GetCourseAPIError as exc:
        if exc.status_code == 200 and is_export_not_ready_payload(exc.detail):
            return {
                "ok": True,
                "data": trim_json(redact(exc.detail), max_items=max_items),
                "export_id": safe_export_id,
                "pending": True,
                "message": "Export is still pending; call getcourse_export_get later.",
            }
        raise

    result = _ok(data, max_items=max_items)
    result["export_id"] = safe_export_id
    result["pending"] = is_export_pending_payload(data)
    return result


async def _wait_for_export(
    export_id: str,
    *,
    attempts: int = 5,
    interval_seconds: float = 2.0,
    max_items: int = 25,
) -> dict[str, Any]:
    bounded_attempts = _bounded_int(
        attempts,
        minimum=1,
        maximum=MAX_POLL_ATTEMPTS,
        name="attempts",
    )
    bounded_interval = _bounded_float(
        interval_seconds,
        minimum=0.0,
        maximum=MAX_POLL_INTERVAL_SECONDS,
        name="interval_seconds",
    )

    last_result: dict[str, Any] | None = None
    for attempt in range(1, bounded_attempts + 1):
        last_result = await _read_export(export_id, max_items=max_items)
        last_result["attempt"] = attempt
        last_result["attempts"] = bounded_attempts
        if not last_result.get("pending"):
            return last_result
        if attempt < bounded_attempts and bounded_interval:
            await asyncio.sleep(bounded_interval)

    assert last_result is not None
    last_result["ok"] = True
    last_result["pending"] = True
    last_result["message"] = "Export is still pending; call getcourse_export_get later."
    return last_result


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
        return await _start_export(dataset, params=params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_export_get(export_id: str, max_items: int = 25) -> dict:
    """Read a GetCourse export result by export id."""
    try:
        return await _read_export(export_id, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_export_wait(
    export_id: str,
    attempts: int = 5,
    interval_seconds: float = 2.0,
    max_items: int = 25,
) -> dict:
    """Poll a GetCourse export with bounded attempts and interval."""
    try:
        return await _wait_for_export(
            export_id,
            attempts=attempts,
            interval_seconds=interval_seconds,
            max_items=max_items,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_group_users_export(
    group_id: str,
    status: str | None = None,
    added_from: str | None = None,
    added_to: str | None = None,
    max_items: int = 25,
) -> dict:
    """Start a filtered GetCourse export of users from a group."""
    try:
        safe_group_id = group_id.strip()
        if not safe_group_id:
            raise GetCourseAPIError("group_id is required", 400)

        params: dict[str, Any] = {"status": status}
        _add_range(params, "added_at", added_from, added_to)
        params = _compact_params(params)
        _require_filter(params, "group_users")

        data = await _get_client().get(f"/pl/api/account/groups/{safe_group_id}/users", params=params)
        return _ok(data, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_users_export_start(
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    added_from: str | None = None,
    added_to: str | None = None,
    max_items: int = 25,
) -> dict:
    """Start a users export with typed safe filters."""
    try:
        params = _build_user_filters(
            status=status,
            created_from=created_from,
            created_to=created_to,
            added_from=added_from,
            added_to=added_to,
        )
        _require_filter(params, "users")
        return await _start_export("users", params=params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_deals_export_start(
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    payed_from: str | None = None,
    payed_to: str | None = None,
    finished_from: str | None = None,
    finished_to: str | None = None,
    status_changed_from: str | None = None,
    status_changed_to: str | None = None,
    user_id: str | None = None,
    user_in_group: str | None = None,
    max_items: int = 25,
) -> dict:
    """Start a deals export with typed safe filters."""
    try:
        params = _build_deal_filters(
            status=status,
            created_from=created_from,
            created_to=created_to,
            payed_from=payed_from,
            payed_to=payed_to,
            finished_from=finished_from,
            finished_to=finished_to,
            status_changed_from=status_changed_from,
            status_changed_to=status_changed_to,
            user_id=user_id,
            user_in_group=user_in_group,
        )
        _require_filter(params, "deals")
        return await _start_export("deals", params=params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_payments_export_start(
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    status_changed_from: str | None = None,
    status_changed_to: str | None = None,
    max_items: int = 25,
) -> dict:
    """Start a payments export with typed safe filters."""
    try:
        params = _build_payment_filters(
            status=status,
            created_from=created_from,
            created_to=created_to,
            status_changed_from=status_changed_from,
            status_changed_to=status_changed_to,
        )
        _require_filter(params, "payments")
        return await _start_export("payments", params=params, max_items=max_items)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_users_export_wait(
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    added_from: str | None = None,
    added_to: str | None = None,
    attempts: int = 5,
    interval_seconds: float = 2.0,
    max_items: int = 25,
) -> dict:
    """Start a filtered users export and poll it with bounded attempts."""
    try:
        start_result = await getcourse_users_export_start(
            status=status,
            created_from=created_from,
            created_to=created_to,
            added_from=added_from,
            added_to=added_to,
            max_items=max_items,
        )
        export_id = start_result.get("export_id")
        if not start_result.get("ok") or not export_id:
            return start_result
        wait_result = await _wait_for_export(
            export_id,
            attempts=attempts,
            interval_seconds=interval_seconds,
            max_items=max_items,
        )
        wait_result["started"] = trim_json(start_result, max_items=max_items)
        return wait_result
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_deals_export_wait(
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    payed_from: str | None = None,
    payed_to: str | None = None,
    finished_from: str | None = None,
    finished_to: str | None = None,
    status_changed_from: str | None = None,
    status_changed_to: str | None = None,
    user_id: str | None = None,
    user_in_group: str | None = None,
    attempts: int = 5,
    interval_seconds: float = 2.0,
    max_items: int = 25,
) -> dict:
    """Start a filtered deals export and poll it with bounded attempts."""
    try:
        start_result = await getcourse_deals_export_start(
            status=status,
            created_from=created_from,
            created_to=created_to,
            payed_from=payed_from,
            payed_to=payed_to,
            finished_from=finished_from,
            finished_to=finished_to,
            status_changed_from=status_changed_from,
            status_changed_to=status_changed_to,
            user_id=user_id,
            user_in_group=user_in_group,
            max_items=max_items,
        )
        export_id = start_result.get("export_id")
        if not start_result.get("ok") or not export_id:
            return start_result
        wait_result = await _wait_for_export(
            export_id,
            attempts=attempts,
            interval_seconds=interval_seconds,
            max_items=max_items,
        )
        wait_result["started"] = trim_json(start_result, max_items=max_items)
        return wait_result
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_user_import(
    params: dict,
    confirm_write: bool = False,
    max_items: int = 25,
) -> dict:
    """Create or refresh a user through GetCourse Import API; requires confirm_write=True."""
    try:
        return await _post_import(
            resource="users",
            action="add",
            params=params,
            confirm_write=confirm_write,
            max_items=max_items,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_user_groups_update(
    user_id: str,
    group_names: list[str],
    confirm_write: bool = False,
    max_items: int = 25,
) -> dict:
    """Replace a user's group list through GetCourse Import API; requires confirm_write=True."""
    try:
        clean_user_id = str(user_id).strip()
        clean_group_names = [str(name).strip() for name in group_names if str(name).strip()]
        if not clean_user_id:
            raise GetCourseAPIError("user_id is required", 400)
        if not clean_group_names:
            raise GetCourseAPIError("group_names must contain at least one group", 400)
        return await _post_import(
            resource="users",
            action="update",
            params={"user": {"id": clean_user_id, "group_name": clean_group_names}},
            confirm_write=confirm_write,
            max_items=max_items,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_deal_import(
    params: dict,
    confirm_write: bool = False,
    max_items: int = 25,
) -> dict:
    """Create or update a deal through GetCourse Import API; requires confirm_write=True."""
    try:
        return await _post_import(
            resource="deals",
            action="add",
            params=params,
            confirm_write=confirm_write,
            max_items=max_items,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
async def getcourse_deal_status_update(
    email: str,
    deal_number: str,
    deal_status: str,
    confirm_write: bool = False,
    max_items: int = 25,
) -> dict:
    """Update a deal status through GetCourse Import API; requires confirm_write=True."""
    try:
        clean_email = email.strip()
        clean_deal_number = deal_number.strip()
        clean_deal_status = deal_status.strip()
        if not clean_email:
            raise GetCourseAPIError("email is required", 400)
        if not clean_deal_number:
            raise GetCourseAPIError("deal_number is required", 400)
        if not clean_deal_status:
            raise GetCourseAPIError("deal_status is required", 400)
        return await _post_import(
            resource="deals",
            action="add",
            params={
                "user": {"email": clean_email},
                "deal": {
                    "deal_number": clean_deal_number,
                    "deal_status": clean_deal_status,
                },
            },
            confirm_write=confirm_write,
            max_items=max_items,
        )
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
