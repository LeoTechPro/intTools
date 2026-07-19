import argparse
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from vakas_mcp.api_manifest import load_manifest
from vakas_mcp.client import VakasClient, VakasError, normalize_payload, payload_summary, validate_destination
from vakas_mcp.config import Config, ConfigError


mcp = FastMCP("Vakas MCP Server")
_config: Config | None = None
_client: VakasClient | None = None


def _load_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def _get_client(config: Config) -> VakasClient:
    global _client
    if _client is None:
        _client = VakasClient(
            timeout_seconds=config.timeout_seconds,
            dedupe_ttl_seconds=config.dedupe_ttl_seconds,
        )
    return _client


def _error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, VakasError):
        return {
            "ok": False,
            "error": exc.message,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "redacted": True,
        }
    if isinstance(exc, ConfigError):
        return {
            "ok": False,
            "error": str(exc),
            "error_code": "configuration_error",
            "status_code": 500,
            "redacted": True,
        }
    return {
        "ok": False,
        "error": "Unexpected Vakas MCP error",
        "error_code": "internal_error",
        "status_code": 500,
        "redacted": True,
    }


def _endpoint_state(endpoint: str | None) -> str:
    if not endpoint:
        return "unset"
    try:
        validate_destination(endpoint)
    except VakasError:
        return "invalid"
    return "configured_allowlisted"


@mcp.tool()
async def vakas_health() -> dict[str, Any]:
    """Report safe configuration metadata without endpoint or payload values."""
    try:
        config = _load_config()
        return {
            "ok": True,
            "mode": "ingress_only",
            "management_api": False,
            "events": {
                event_type: {
                    "endpoint_state": _endpoint_state(config.endpoints[event_type]),
                    "source": config.endpoint_sources[event_type],
                }
                for event_type in sorted(config.endpoints)
            },
            "dry_run_default": True,
            "confirm_write_required": True,
            "idempotency_scope": "process_local",
            "allowed_destination": "HTTPS Vakas-tools host only",
            "redacted": True,
        }
    except Exception as exc:
        return _error(exc)


@mcp.tool()
async def vakas_api_manifest() -> dict[str, Any]:
    """Return safe coverage metadata for the documented Vakas ingress API."""
    try:
        manifest = load_manifest()
        return {
            "ok": True,
            "mode": "ingress_only",
            "management_api": False,
            "official_source": manifest["official_source"],
            "verified_on": manifest["verified_on"],
            "surface_count": len(manifest["surfaces"]),
            "surfaces": [
                {
                    "id": row["id"],
                    "official_methods": row["official_methods"],
                    "transport_method": row["transport_method"],
                    "risk": row["risk"],
                    "fields": row["fields"],
                    "tools": row["tools"],
                }
                for row in manifest["surfaces"]
            ],
            "redacted": True,
        }
    except Exception as exc:
        return _error(exc)


@mcp.tool()
async def vakas_validate_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a documented registration, report or order payload locally."""
    try:
        safe_event_type = event_type.strip().lower()
        normalized = normalize_payload(safe_event_type, payload)
        return {
            "ok": True,
            "valid": True,
            "dry_run": True,
            "network_attempted": False,
            "summary": payload_summary(safe_event_type, normalized),
        }
    except Exception as exc:
        return _error(exc)


async def _submit(
    event_type: str,
    payload: dict[str, Any],
    *,
    idempotency_key: str | None,
    confirm_write: bool,
) -> dict[str, Any]:
    try:
        normalized = normalize_payload(event_type, payload)
        summary = payload_summary(event_type, normalized)
        config = _load_config()
        endpoint = config.endpoints[event_type]
        if confirm_write is not True:
            return {
                "ok": True,
                "valid": True,
                "dry_run": True,
                "network_attempted": False,
                "dispatch_blocked": "confirm_write_true_required",
                "endpoint_configured": bool(endpoint),
                "summary": summary,
            }
        if not endpoint:
            raise VakasError("endpoint_not_configured", f"{event_type} endpoint is not configured", status_code=503)
        safe_key = (idempotency_key or "").strip()
        if not safe_key:
            raise VakasError("idempotency_key_required", "idempotency_key is required for dispatch")
        result = await _get_client(config).dispatch(
            event_type=event_type,
            endpoint=endpoint,
            payload=normalized,
            idempotency_key=safe_key,
        )
        return {
            "ok": result.accepted,
            "dry_run": False,
            "network_attempted": True,
            "status_code": result.status_code,
            "accepted": result.accepted,
            "idempotency_scope": "process_local",
            "summary": summary,
            "redacted": True,
        }
    except Exception as exc:
        return _error(exc)


@mcp.tool()
async def vakas_submit_registration(
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    confirm_write: bool = False,
) -> dict[str, Any]:
    """Validate a registration; dispatch only with confirmation and an idempotency key."""
    return await _submit(
        "registration", payload, idempotency_key=idempotency_key, confirm_write=confirm_write
    )


@mcp.tool()
async def vakas_submit_report(
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    confirm_write: bool = False,
) -> dict[str, Any]:
    """Validate a webinar report; dispatch only with confirmation and an idempotency key."""
    return await _submit("report", payload, idempotency_key=idempotency_key, confirm_write=confirm_write)


@mcp.tool()
async def vakas_submit_order(
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    confirm_write: bool = False,
) -> dict[str, Any]:
    """Validate an order; dispatch only with confirmation and an idempotency key."""
    return await _submit("order", payload, idempotency_key=idempotency_key, confirm_write=confirm_write)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the guarded Vakas MCP server")
    parser.add_argument("--transport", choices=("stdio", "sse", "streamable-http"))
    parser.add_argument("--port", type=int)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        config = _load_config()
    except ConfigError as exc:
        print(f"vakas-mcp configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    for logger_name in ("httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    transport = args.transport or config.transport
    port = args.port or config.port
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.port = port
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
