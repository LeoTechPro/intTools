from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from .models import PolicyDecision, ToolCallRequest


@dataclass(frozen=True)
class AuditEntry:
    id: str
    created_at: str
    request_id: str
    source_facade: str
    principal: dict[str, Any]
    tool: str
    policy_decision_id: str
    policy_allowed: bool
    policy_reason: str
    status: str
    result_meta: dict[str, Any]


class AuditStore(Protocol):
    def record(
        self,
        request: ToolCallRequest,
        decision: PolicyDecision,
        status: str,
        result: Any | None = None,
        error: dict[str, Any] | None = None,
    ) -> AuditEntry:
        ...

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        ...


class MemoryAuditStore:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(
        self,
        request: ToolCallRequest,
        decision: PolicyDecision,
        status: str,
        result: Any | None = None,
        error: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = _make_entry(request, decision, status, result=result, error=error)
        self._entries.append(entry)
        return entry

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in self._entries[-limit:]]


class JsonlAuditStore(MemoryAuditStore):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        request: ToolCallRequest,
        decision: PolicyDecision,
        status: str,
        result: Any | None = None,
        error: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = super().record(request, decision, status, result=result, error=error)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True) + "\n")
        return entry


class PostgresAuditStore:
    def __init__(self, dsn: str) -> None:
        try:
            import psycopg2  # type: ignore[import-not-found]
            import psycopg2.extras  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("psycopg2 is required when AGENT_PLANE_DATABASE_URL is set") from exc
        self._psycopg2 = psycopg2
        self._extras = psycopg2.extras
        self._dsn = dsn

    def record(
        self,
        request: ToolCallRequest,
        decision: PolicyDecision,
        status: str,
        result: Any | None = None,
        error: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = _make_entry(request, decision, status, result=result, error=error)
        with self._psycopg2.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into agent_plane.policy_decisions (
                        id, request_id, source_facade, principal, tool,
                        allowed, reason, guarded, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do nothing
                    """,
                    (
                        entry.policy_decision_id,
                        entry.request_id,
                        entry.source_facade,
                        self._extras.Json(entry.principal),
                        entry.tool,
                        entry.policy_allowed,
                        entry.policy_reason,
                        decision.guarded,
                        entry.created_at,
                    ),
                )
                cur.execute(
                    """
                    insert into agent_plane.tool_calls (
                        id, request_id, source_facade, principal, tool,
                        policy_decision_id, policy_allowed, policy_reason,
                        status, result_meta, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entry.id,
                        entry.request_id,
                        entry.source_facade,
                        self._extras.Json(entry.principal),
                        entry.tool,
                        entry.policy_decision_id,
                        entry.policy_allowed,
                        entry.policy_reason,
                        entry.status,
                        self._extras.Json(entry.result_meta),
                        entry.created_at,
                    ),
                )
        return entry

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._psycopg2.connect(self._dsn) as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    select id, request_id, source_facade, principal, tool,
                           policy_decision_id, policy_allowed, policy_reason,
                           status, result_meta, created_at
                    from agent_plane.tool_calls
                    order by created_at desc
                    limit %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]


def create_audit_store() -> AuditStore:
    dsn = os.getenv("AGENT_PLANE_DATABASE_URL", "").strip()
    if dsn:
        return PostgresAuditStore(dsn)
    default_path = Path(os.getenv("AGENT_PLANE_AUDIT_JSONL", str(Path(__file__).resolve().parents[1] / ".runtime" / "agent-plane" / "audit.jsonl")))
    return JsonlAuditStore(default_path)


def _make_entry(
    request: ToolCallRequest,
    decision: PolicyDecision,
    status: str,
    result: Any | None = None,
    error: dict[str, Any] | None = None,
) -> AuditEntry:
    return AuditEntry(
        id=str(uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        request_id=request.request_id,
        source_facade=request.source_facade,
        principal=_sanitize_json(request.principal),
        tool=request.tool,
        policy_decision_id=decision.decision_id,
        policy_allowed=decision.allowed,
        policy_reason=decision.reason,
        status=status,
        result_meta=_result_meta(result=result, error=error),
    )


def _result_meta(result: Any | None = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    if error is not None:
        return {"error": _sanitize_json(error)}
    if isinstance(result, dict):
        return {"keys": sorted(str(key) for key in result.keys()), "type": "object"}
    if isinstance(result, list):
        return {"items": len(result), "type": "array"}
    return {"type": type(result).__name__}


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(secret in key_text.lower() for secret in ("token", "secret", "key", "password")):
                sanitized[key_text] = "<redacted>"
            else:
                sanitized[key_text] = _sanitize_json(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    return value
