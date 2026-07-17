"""Umnico tools for omnichannel conversations linked to amoCRM."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from amocrm_mcp.client import error_response, success_response
from amocrm_mcp.server import execute_umnico_tool, mcp


class LeadsListInput(BaseModel):
    section: Literal["inbox", "active", "completed", "all"] = "active"
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
    types: list[str] | None = None
    statuses: list[int] | None = None
    integration_ids: list[int] | None = None
    manager_ids: list[int] | None = None
    unread: list[Literal["unread", "read", "unanswered", "answered"]] | None = None


class FindLeadsInput(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    sections: list[Literal["inbox", "active", "completed"]] = Field(
        default_factory=lambda: ["inbox", "active", "completed"]
    )
    limit_per_section: int = Field(default=200, ge=1, le=200)


class LeadInput(BaseModel):
    lead_id: int = Field(gt=0)


class HistoryInput(LeadInput):
    source_real_id: int = Field(gt=0)
    cursor: int | str | None = None


class SendToLeadInput(LeadInput):
    source: int | str
    user_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=10000)
    sa_id: int | None = Field(default=None, gt=0)
    custom_id: str | None = Field(default=None, max_length=200)
    reply_id: int | str | None = None
    confirm_send: bool = False


class SendFirstInput(BaseModel):
    destination: str = Field(min_length=1, max_length=320)
    sa_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=10000)
    custom_id: str | None = Field(default=None, max_length=200)
    confirm_send: bool = False


def _lead_search_text(lead: dict) -> str:
    customer = lead.get("customer") or {}
    message = lead.get("message") or {}
    message_data = message.get("data") or {}
    values = [
        lead.get("id"),
        customer.get("id"),
        customer.get("name"),
        customer.get("login"),
        customer.get("email"),
        customer.get("phone"),
        message_data.get("text"),
    ]
    return " ".join(str(value) for value in values if value is not None).casefold()


def _matches_query(lead: dict, query: str) -> bool:
    haystack = _lead_search_text(lead)
    needle = query.strip().casefold()
    if needle in haystack:
        return True
    digits = re.sub(r"\D", "", needle)
    return len(digits) >= 7 and digits in re.sub(r"\D", "", haystack)


@mcp.tool()
async def umnico_account_get() -> dict:
    """Read the active Umnico account status. Does not expose the API key."""

    async def _execute(client):
        return success_response(await client.request("GET", "/account/me"))

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_integrations_list() -> dict:
    """List connected messaging integrations and their statuses."""

    async def _execute(client):
        return success_response(await client.request("GET", "/integrations"))

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_managers_list() -> dict:
    """List Umnico managers, IDs, roles and amoCRM mappings."""

    async def _execute(client):
        return success_response(await client.request("GET", "/managers"))

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_leads_list(input: LeadsListInput) -> dict:
    """List Umnico conversations from inbox, active, completed or all sections."""

    async def _execute(client):
        params: dict = {"offset": input.offset, "limit": input.limit}
        if input.types:
            params["types"] = input.types
        if input.statuses:
            params["statuses"] = input.statuses
        if input.integration_ids:
            params["sa"] = input.integration_ids
        if input.manager_ids:
            params["users"] = input.manager_ids
        if input.unread:
            params["unread"] = input.unread
        data = await client.request("GET", f"/leads/{input.section}", params=params)
        return success_response(data, {"offset": input.offset, "limit": input.limit})

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_find_leads(input: FindLeadsInput) -> dict:
    """Find conversations by name, phone, email, IDs or recent message text.

    Uses account-JWT-compatible list endpoints instead of OAuth-only Umnico search.
    """

    async def _execute(client):
        matches: list[dict] = []
        seen: set[int | str] = set()
        for section in input.sections:
            leads = await client.request(
                "GET",
                f"/leads/{section}",
                params={"offset": 0, "limit": input.limit_per_section},
            )
            for lead in leads if isinstance(leads, list) else []:
                if not isinstance(lead, dict) or not _matches_query(lead, input.query):
                    continue
                lead_id = lead.get("id")
                if lead_id in seen:
                    continue
                seen.add(lead_id)
                matches.append({"section": section, **lead})
        return success_response(matches, {"scanned_sections": input.sections})

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_lead_get(input: LeadInput) -> dict:
    """Read a single Umnico conversation by ID."""

    async def _execute(client):
        return success_response(await client.request("GET", f"/leads/{input.lead_id}"))

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_sources_list(input: LeadInput) -> dict:
    """List available message channels for a conversation before replying."""

    async def _execute(client):
        return success_response(await client.request("GET", f"/messaging/{input.lead_id}/sources"))

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_history_get(input: HistoryInput) -> dict:
    """Read message history for one conversation channel."""

    async def _execute(client):
        payload = {"cursor": input.cursor} if input.cursor is not None else {}
        data = await client.request(
            "POST",
            f"/messaging/{input.lead_id}/history/{input.source_real_id}",
            json_data=payload,
        )
        return success_response(data)

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_send_to_lead(input: SendToLeadInput) -> dict:
    """Send a text reply to an existing Umnico conversation.

    Outward communication is blocked unless confirm_send is explicitly true.
    Read sources and managers first; never guess source, sa_id or user_id.
    """
    if not input.confirm_send:
        return error_response(
            "Explicit confirmation required",
            409,
            "Review recipient, channel and final text, then repeat with confirm_send=true.",
        )

    async def _execute(client):
        payload: dict = {
            "message": {"text": input.text},
            "source": input.source,
            "userId": input.user_id,
        }
        if input.sa_id is not None:
            payload["saId"] = input.sa_id
        if input.custom_id:
            payload["customId"] = input.custom_id
        if input.reply_id is not None:
            payload["replyId"] = input.reply_id
        return success_response(
            await client.request("POST", f"/messaging/{input.lead_id}/send", json_data=payload)
        )

    return await execute_umnico_tool(_execute)


@mcp.tool()
async def umnico_send_first(input: SendFirstInput) -> dict:
    """Start a new WhatsApp, Telegram Personal or mailbox conversation.

    Outward communication is blocked unless confirm_send is explicitly true.
    Confirm that the chosen integration supports write-first and comply with its limits.
    """
    if not input.confirm_send:
        return error_response(
            "Explicit confirmation required",
            409,
            "Review destination, integration and final text, then repeat with confirm_send=true.",
        )

    async def _execute(client):
        payload: dict = {
            "message": {"text": input.text},
            "destination": input.destination,
            "saId": input.sa_id,
        }
        if input.custom_id:
            payload["customId"] = input.custom_id
        return success_response(await client.request("POST", "/messaging/post", json_data=payload))

    return await execute_umnico_tool(_execute)
