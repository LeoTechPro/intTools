#!/usr/bin/env python3
"""Safety guard helpers for review-sql-fix pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

ALLOWED_ENVIRONMENTS = {"dev", "stage", "prod"}
ALLOWED_SCOPES = {"int/data", "int/assess", "custom"}
ALLOWED_FIX_MODES = {"apply", "plan_only"}
ALLOWED_SOURCES = {"live_sql", "section_summaries"}

DANGEROUS_SQL_PATTERNS = [
    re.compile(r"\bdrop\s+database\b", re.IGNORECASE),
    re.compile(r"\bdrop\s+schema\b", re.IGNORECASE),
    re.compile(r"\bdrop\s+table\b", re.IGNORECASE),
    re.compile(r"\btruncate\b", re.IGNORECASE),
    re.compile(r"\bvacuum\s+full\b", re.IGNORECASE),
    re.compile(r"\breindex\s+database\b", re.IGNORECASE),
    re.compile(r"\balter\s+system\s+reset\s+all\b", re.IGNORECASE),
    re.compile(r"\bdelete\s+from\b(?!.*\bwhere\b)", re.IGNORECASE | re.DOTALL),
]


class SafetyGuardError(Exception):
    """Raised when payload violates hard safety rules."""


@dataclass
class PolicyDecision:
    environment: str
    scope: str
    source: str
    requested_fix_mode: str
    effective_mode: str
    allow_apply: bool
    allow_dangerous: bool
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "scope": self.scope,
            "source": self.source,
            "requested_fix_mode": self.requested_fix_mode,
            "effective_mode": self.effective_mode,
            "allow_apply": self.allow_apply,
            "allow_dangerous": self.allow_dangerous,
            "notes": list(self.notes),
        }


def _norm_text(value: Any, *, default: str = "") -> str:
    text = str(value or default).strip().lower()
    return text


def _require_payload_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SafetyGuardError("input payload must be a JSON object")
    return payload


def _validate_in(value: str, allowed: set[str], field_name: str) -> None:
    if value not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise SafetyGuardError(f"invalid '{field_name}': {value}. allowed: {allowed_list}")


def is_dangerous_sql(sql: str) -> bool:
    text = sql.strip()
    for pattern in DANGEROUS_SQL_PATTERNS:
        if pattern.search(text):
            return True
    return False


def enforce(payload: Any) -> PolicyDecision:
    data = _require_payload_object(payload)

    environment = _norm_text(data.get("environment"))
    scope = _norm_text(data.get("scope"))
    source = _norm_text(data.get("source"))
    requested_fix_mode = _norm_text(data.get("fix_mode"), default="apply")
    allow_dangerous = bool(data.get("allow_dangerous", False))

    if not environment:
        raise SafetyGuardError("missing required field: environment")
    if not scope:
        raise SafetyGuardError("missing required field: scope")
    if not source:
        raise SafetyGuardError("missing required field: source")

    _validate_in(environment, ALLOWED_ENVIRONMENTS, "environment")
    _validate_in(scope, ALLOWED_SCOPES, "scope")
    _validate_in(source, ALLOWED_SOURCES, "source")
    _validate_in(requested_fix_mode, ALLOWED_FIX_MODES, "fix_mode")

    findings_bundle = data.get("findings_bundle")
    if findings_bundle is None:
        raise SafetyGuardError("missing required field: findings_bundle")

    repo_fixes = data.get("repo_fixes") or []
    repo_targets = data.get("repo_targets") or []
    if repo_fixes and not repo_targets:
        raise SafetyGuardError("repo_targets is required when repo_fixes is provided")

    notes: list[str] = []
    effective_mode = requested_fix_mode
    allow_apply = requested_fix_mode == "apply"

    if environment == "prod" and requested_fix_mode == "apply":
        effective_mode = "plan_only"
        allow_apply = False
        notes.append("prod guard: apply disabled, switched to plan_only")

    if effective_mode == "plan_only":
        allow_apply = False
        notes.append("effective mode is plan_only")

    return PolicyDecision(
        environment=environment,
        scope=scope,
        source=source,
        requested_fix_mode=requested_fix_mode,
        effective_mode=effective_mode,
        allow_apply=allow_apply,
        allow_dangerous=allow_dangerous,
        notes=notes,
    )


def assert_runtime_sql_safe(sql_statements: list[str], allow_dangerous: bool) -> None:
    if allow_dangerous:
        return

    dangerous_hits: list[str] = []
    for sql in sql_statements:
        if is_dangerous_sql(sql):
            dangerous_hits.append(sql)

    if dangerous_hits:
        raise SafetyGuardError(
            "dangerous SQL is blocked by policy; set allow_dangerous=true to override"
        )
