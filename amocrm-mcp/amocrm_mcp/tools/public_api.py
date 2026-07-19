"""Manifest-backed access to every documented amoCRM HTTP endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from amocrm_mcp.api_manifest import endpoint_index, get_endpoint, load_manifest
from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.server import execute_tool, mcp


class PublicApiCallInput(BaseModel):
    endpoint_id: str = Field(description="Stable id returned by amocrm_api_endpoints")
    path_parameters: dict[str, str | int] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Endpoint-specific headers such as Content-Range; auth and Host cannot be overridden",
    )
    body: Any | None = None
    content_base64: str | None = Field(
        default=None,
        description="Base64 payload for binary Files API uploads; mutually exclusive with body",
    )
    content_type: str | None = None


class EndpointListInput(BaseModel):
    surface: str | None = Field(default=None, description="rest, webhooks, chats, files, or telephony")
    method: str | None = None
    query: str | None = Field(default=None, description="Substring search over id and path")


@mcp.tool()
async def amocrm_api_endpoints(input: EndpointListInput) -> dict:
    """List the committed official API endpoint registry used for parity checks."""
    rows = list(endpoint_index().values())
    if input.surface:
        rows = [row for row in rows if row["surface"] == input.surface.lower()]
    if input.method:
        rows = [row for row in rows if row["method"] == input.method.upper()]
    if input.query:
        needle = input.query.lower()
        rows = [row for row in rows if needle in row["id"].lower() or needle in row["path"].lower()]
    return success_response(rows)


@mcp.tool()
async def amocrm_api_manifest() -> dict:
    """Return parity metadata, official sources, exclusions, and endpoint totals."""
    manifest = load_manifest()
    counts: dict[str, int] = {}
    for endpoint in manifest["endpoints"]:
        counts[endpoint["surface"]] = counts.get(endpoint["surface"], 0) + 1
    return success_response(
        {
            "schema_version": manifest["schema_version"],
            "endpoint_count": len(manifest["endpoints"]),
            "counts_by_surface": counts,
            "generated_from": manifest["generated_from"],
            "excluded_surfaces": manifest["excluded_surfaces"],
        }
    )


@mcp.tool()
async def amocrm_api_call(input: PublicApiCallInput) -> dict:
    """Call any registered public amoCRM REST, Webhooks, Chats, Files, or telephony endpoint.

    This tool intentionally has no connector-specific confirmation switch. Runtime
    policy remains the responsibility of the MCP host (Codex or Hermes).
    """
    try:
        endpoint = get_endpoint(input.endpoint_id)
    except ValueError as exc:
        return error_response("Unknown endpoint", 400, str(exc))

    async def _execute(client):
        if input.body is not None and input.content_base64 is not None:
            raise AmoAPIError(400, "Invalid payload", "body and content_base64 are mutually exclusive")
        data = await client.request_public_endpoint(
            endpoint=endpoint,
            path_parameters=input.path_parameters,
            params=input.query or None,
            extra_headers=input.headers or None,
            body=input.body,
            content_base64=input.content_base64,
            content_type=input.content_type,
        )
        return success_response(data)

    return await execute_tool(_execute)
