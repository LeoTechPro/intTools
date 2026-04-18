from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


ALLOWED_FACADES = {"agno", "openclaw", "codex_app"}


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ToolCallRequest:
    request_id: str
    facade: str
    principal: dict[str, Any]
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    approval_ref: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ToolCallRequest":
        if not isinstance(payload, dict):
            raise ValidationError("request payload must be an object")

        request_id = str(payload.get("request_id") or uuid4())
        facade = str(payload.get("facade") or "").strip()
        if facade not in ALLOWED_FACADES:
            raise ValidationError(f"unknown facade: {facade or '<empty>'}")

        principal = payload.get("principal") or {}
        if not isinstance(principal, dict):
            raise ValidationError("principal must be an object")
        if not _has_principal_identity(principal):
            raise ValidationError("principal must include id, user_id, chat_id, or agent_id")

        tool = str(payload.get("tool") or "").strip()
        if not tool:
            raise ValidationError("tool is required")
        if _is_cabinet_tool(tool):
            raise ValidationError("cabinet tools are out of scope for agent plane")

        args = payload.get("args") or {}
        if not isinstance(args, dict):
            raise ValidationError("args must be an object")

        context = payload.get("context") or {}
        if not isinstance(context, dict):
            raise ValidationError("context must be an object")

        approval_ref = payload.get("approval_ref")
        if approval_ref is not None:
            approval_ref = str(approval_ref).strip() or None

        return cls(
            request_id=request_id,
            facade=facade,
            principal=principal,
            tool=tool,
            args=args,
            context=context,
            dry_run=bool(payload.get("dry_run", False)),
            approval_ref=approval_ref,
        )

    @property
    def source_facade(self) -> str:
        return self.facade


@dataclass(frozen=True)
class PolicyDecision:
    decision_id: str
    allowed: bool
    reason: str
    guarded: bool = False


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    result: Any | None = None
    error: dict[str, Any] | None = None


def _has_principal_identity(principal: dict[str, Any]) -> bool:
    return any(principal.get(key) for key in ("id", "user_id", "chat_id", "agent_id"))


def _is_cabinet_tool(tool: str) -> bool:
    return tool.startswith("cabinet_") or tool.startswith("cabinet.") or "_cabinet_" in tool or tool.endswith("_cabinet")
