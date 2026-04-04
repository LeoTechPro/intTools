#!/usr/bin/env python3
"""Compile deterministic PostgreSQL audit reports from normalized section data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_SECTIONS: list[tuple[str, str, str]] = [
    ("access_control_roles", "Access Control & Roles", "security"),
    ("network_security", "Network Security", "security"),
    ("auth_ssl", "Authentication & SSL", "security"),
    ("audit_logging", "Audit & Logging", "security"),
    ("connection_management", "Connection Management", "performance"),
    ("query_performance", "Query Performance", "performance"),
    ("wal_checkpoint", "WAL & Checkpoint", "performance"),
    ("autovacuum", "Autovacuum", "performance"),
    ("planner_settings", "Query Planner Settings", "performance"),
    ("parallelism_workers", "Parallelism & Workers", "performance"),
    ("extensions", "Extensions", "security"),
    ("cache_efficiency", "Cache Efficiency", "performance"),
    ("replication_status", "Replication Status", "performance"),
]

SECTION_META: dict[str, dict[str, str]] = {
    section_id: {"title": title, "category": category}
    for section_id, title, category in REQUIRED_SECTIONS
}

SEVERITY_ORDER = {
    "incomplete": 4,
    "critical": 3,
    "warning": 2,
    "advisory": 1,
    "good": 0,
}

TRUNCATION_MARKERS = (
    "<Truncated in logs>",
    "Synthesis failed",
)

TAIL_PATTERNS = [
    re.compile(r"(?mi)^\s*[-*]\s*(?:[\W_]*?)real\s*$"),
    re.compile(r"(?mi)^\s*[-*].*\bfor\s*$"),
]


class ValidationError(Exception):
    """Input data is invalid for deterministic report synthesis."""



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile PostgreSQL audit markdown reports")
    parser.add_argument("--input", required=True, help="Path to normalized audit JSON")
    parser.add_argument("--output-dir", required=True, help="Directory for output markdown files")
    return parser.parse_args()



def _normalize_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized
    text = str(value).strip()
    return [text] if text else []



def _status_normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text == "":
        return "INCOMPLETE"
    if text == "incomplete":
        return "INCOMPLETE"
    if text in ("critical", "warning", "advisory", "good"):
        return text.title()
    return "INCOMPLETE"



def normalize_sections(payload: dict[str, Any]) -> OrderedDict[str, dict[str, Any]]:
    raw_sections = payload.get("sections")
    if raw_sections is None:
        raw_sections = payload.get("input_sections")
    if raw_sections is None:
        raise ValidationError("Missing 'sections' (or fallback 'input_sections') in input payload")

    items: list[dict[str, Any]] = []
    if isinstance(raw_sections, list):
        for entry in raw_sections:
            if isinstance(entry, dict):
                items.append(dict(entry))
    elif isinstance(raw_sections, dict):
        for key, entry in raw_sections.items():
            if isinstance(entry, dict):
                section = dict(entry)
                section.setdefault("id", key)
                items.append(section)
    else:
        raise ValidationError("'sections' must be a list or object map")

    if not items:
        raise ValidationError("No section entries found in input payload")

    normalized: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for entry in items:
        section_id = str(entry.get("id", "")).strip()
        if not section_id:
            continue

        defaults = SECTION_META.get(section_id, {})
        title = str(entry.get("title") or defaults.get("title") or section_id).strip()
        category = str(entry.get("category") or defaults.get("category") or "performance").strip().lower()
        if category not in ("security", "performance"):
            category = defaults.get("category", "performance")

        findings = _normalize_lines(entry.get("findings"))
        recommendations = _normalize_lines(entry.get("recommendations"))

        normalized[section_id] = {
            "id": section_id,
            "title": title,
            "category": category,
            "status": _status_normalize(entry.get("status")),
            "findings": findings,
            "recommendations": recommendations,
            "completeness": str(entry.get("completeness", "")).strip().lower(),
        }

    return normalized



def find_missing_sections(sections: OrderedDict[str, dict[str, Any]]) -> list[str]:
    required_ids = [item[0] for item in REQUIRED_SECTIONS]
    return [section_id for section_id in required_ids if section_id not in sections]



def completeness_failures(section: dict[str, Any]) -> list[str]:
    reasons: list[str] = []

    if section["status"].upper() == "INCOMPLETE":
        reasons.append("status is INCOMPLETE")

    if section.get("completeness") == "incomplete":
        reasons.append("completeness flag is incomplete")

    if not section.get("title"):
        reasons.append("missing title")

    findings = section.get("findings") or []
    if not findings:
        reasons.append("missing findings")

    recommendations = section.get("recommendations") or []
    if not recommendations:
        reasons.append("missing recommendations")

    blob = "\n".join(
        [section.get("title", ""), section.get("status", "")]
        + findings
        + recommendations
    )

    for marker in TRUNCATION_MARKERS:
        if marker in blob:
            reasons.append(f"contains marker: {marker}")

    for pattern in TAIL_PATTERNS:
        if pattern.search(blob):
            reasons.append(f"contains tail pattern: {pattern.pattern}")
            break

    if blob.count("```") % 2 != 0:
        reasons.append("unmatched code fence")

    return reasons



def severity_rank(status: str) -> int:
    return SEVERITY_ORDER.get(status.strip().lower(), SEVERITY_ORDER["incomplete"])



def _format_list(items: list[str], empty_value: str) -> list[str]:
    if not items:
        return [f"- {empty_value}"]
    return [f"- {item}" for item in items]



def render_section(section: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"### {section['title']}")
    lines.append("")
    lines.append(f"**Status**: {section['status']}")
    lines.append("")
    lines.append("**Findings**:")
    lines.extend(_format_list(section["findings"], "No findings provided."))
    lines.append("")
    lines.append("**Recommendations**:")
    lines.extend(_format_list(section["recommendations"], "No recommendations provided."))
    lines.append("")
    return "\n".join(lines)



def build_report(
    *,
    title: str,
    server: str,
    source: str,
    scope: str,
    audit_mode: str,
    sections: list[dict[str, Any]],
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append(f"# {title}: {server}")
    lines.append("")
    lines.append(f"Generated: {timestamp}")
    lines.append("")
    lines.append(f"Input source: `{source}`")
    lines.append(f"Scope: `{scope}`")
    lines.append(f"Audit mode: `{audit_mode}`")
    lines.append("")
    for section in sections:
        lines.append(render_section(section).rstrip())
    return "\n".join(lines).rstrip() + "\n"



def build_summary(
    *,
    server: str,
    source: str,
    scope: str,
    audit_mode: str,
    sections: list[dict[str, Any]],
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    counts = {"Critical": 0, "Warning": 0, "Advisory": 0, "Good": 0}
    for section in sections:
        status = section["status"]
        if status in counts:
            counts[status] += 1

    top_findings: list[str] = []
    for section in sorted(sections, key=lambda s: (-severity_rank(s["status"]), s["id"])):
        if section["status"] not in ("Critical", "Warning"):
            continue
        for finding in section["findings"]:
            top_findings.append(f"[{section['status']}] {section['title']}: {finding}")
            if len(top_findings) >= 8:
                break
        if len(top_findings) >= 8:
            break

    prioritized: list[str] = []
    seen: set[str] = set()
    for section in sorted(sections, key=lambda s: (-severity_rank(s["status"]), s["id"])):
        if section["status"] == "Good":
            continue
        for rec in section["recommendations"]:
            key = rec.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            prioritized.append(rec)

    lines: list[str] = []
    lines.append(f"# Executive Summary + Prioritized Recommendations: {server}")
    lines.append("")
    lines.append(f"Generated: {timestamp}")
    lines.append("")
    lines.append(f"Input source: `{source}`")
    lines.append(f"Scope: `{scope}`")
    lines.append(f"Audit mode: `{audit_mode}`")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        "Critical sections: {critical}; Warning sections: {warning}; Advisory sections: {advisory}; Good sections: {good}.".format(
            critical=counts["Critical"],
            warning=counts["Warning"],
            advisory=counts["Advisory"],
            good=counts["Good"],
        )
    )
    lines.append("")
    lines.append("## Critical Issues")
    lines.append("")
    lines.extend(_format_list(top_findings, "No critical or warning findings."))
    lines.append("")
    lines.append("## Prioritized Recommendations")
    lines.append("")
    if prioritized:
        for idx, rec in enumerate(prioritized, start=1):
            lines.append(f"{idx}. {rec}")
    else:
        lines.append("1. No recommendations generated.")

    return "\n".join(lines).rstrip() + "\n"



def validate_payload(payload: dict[str, Any], sections: OrderedDict[str, dict[str, Any]]) -> None:
    audit_mode = str(payload.get("audit_mode", "read_only")).strip().lower() or "read_only"
    if audit_mode != "read_only":
        raise ValidationError(
            f"Unsupported audit_mode '{audit_mode}'. Only read_only is allowed for this workflow"
        )

    missing = find_missing_sections(sections)
    if missing:
        raise ValidationError(f"Missing required sections: {', '.join(missing)}")

    failed: list[tuple[str, list[str]]] = []
    for section_id in [item[0] for item in REQUIRED_SECTIONS]:
        section = sections[section_id]
        reasons = completeness_failures(section)
        if reasons:
            failed.append((section_id, reasons))

    if failed:
        lines = ["Incomplete sections detected:"]
        for section_id, reasons in failed:
            lines.append(f"- {section_id}: {', '.join(reasons)}")
        raise ValidationError("\n".join(lines))



def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")



def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"Input file does not exist: {input_path}", file=sys.stderr)
        return 2

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print("Invalid input: top-level JSON must be an object", file=sys.stderr)
        return 2

    try:
        sections = normalize_sections(payload)
        validate_payload(payload, sections)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    required_order = [item[0] for item in REQUIRED_SECTIONS]
    ordered_sections = [sections[section_id] for section_id in required_order]

    security_sections = [s for s in ordered_sections if s["category"] == "security"]
    performance_sections = [s for s in ordered_sections if s["category"] == "performance"]

    server = str(payload.get("server") or "unknown-server").strip()
    source = str(payload.get("source") or "section_summaries").strip()
    scope = str(payload.get("scope") or "custom").strip()
    audit_mode = "read_only"

    security_md = build_report(
        title="Server Security Report",
        server=server,
        source=source,
        scope=scope,
        audit_mode=audit_mode,
        sections=security_sections,
    )
    performance_md = build_report(
        title="Server Performance Report",
        server=server,
        source=source,
        scope=scope,
        audit_mode=audit_mode,
        sections=performance_sections,
    )
    summary_md = build_summary(
        server=server,
        source=source,
        scope=scope,
        audit_mode=audit_mode,
        sections=ordered_sections,
    )

    security_path = output_dir / "server-security-report.md"
    performance_path = output_dir / "server-performance-report.md"
    summary_path = output_dir / "executive-summary-and-priorities.md"

    write_text(security_path, security_md)
    write_text(performance_path, performance_md)
    write_text(summary_path, summary_md)

    result = {
        "ok": True,
        "outputs": {
            "security_report": str(security_path),
            "performance_report": str(performance_path),
            "executive_summary": str(summary_path),
        },
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
