#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER = ROOT / "codex" / "bin" / "mcp-intdata-cli.py"

EXPECTED_COUNTS = {
    "intbrain": 27,
    "intdata-control": 35,
    "intdata-runtime": 9,
    "intdb": 1,
}

PLUGIN_DIRS = {
    "intbrain": ROOT / "codex" / "plugins" / "intbrain",
    "intdata-control": ROOT / "codex" / "plugins" / "intdata-control",
    "intdata-runtime": ROOT / "codex" / "plugins" / "intdata-runtime",
    "intdb": ROOT / "codex" / "plugins" / "intdb",
}

TOOL_SKILLS = {
    "intdata-control": {
        "lockctl_acquire": "lockctl",
        "lockctl_renew": "lockctl",
        "lockctl_release_path": "lockctl",
        "lockctl_release_issue": "lockctl",
        "lockctl_status": "lockctl",
        "lockctl_gc": "lockctl",
        "openspec_list": "openspec-read",
        "openspec_show": "openspec-read",
        "openspec_validate": "openspec-read",
        "openspec_status": "openspec-read",
        "openspec_instructions": "openspec-read",
        "openspec_archive": "openspec-mutation",
        "openspec_change": "openspec-mutation",
        "openspec_spec": "openspec-mutation",
        "openspec_new": "openspec-mutation",
        "openspec_exec": "openspec-mutation",
        "multica_issue": "multica-issue-workflow",
        "multica_project": "multica-entities-config",
        "multica_agent": "multica-entities-config",
        "multica_workspace": "multica-entities-config",
        "multica_repo": "multica-entities-config",
        "multica_skill": "multica-entities-config",
        "multica_runtime": "multica-entities-config",
        "multica_config": "multica-entities-config",
        "multica_daemon": "multica-daemon-auth-attachments",
        "multica_attachment": "multica-daemon-auth-attachments",
        "multica_auth": "multica-daemon-auth-attachments",
        "multica_exec": "multica-daemon-auth-attachments",
        "routing_validate": "routing",
        "routing_resolve": "routing",
        "sync_gate": "sync-gate-publish",
        "publish": "sync-gate-publish",
        "gate_status": "gate-receipts-commit-binding",
        "gate_receipt": "gate-receipts-commit-binding",
        "commit_binding": "gate-receipts-commit-binding",
    },
    "intdata-runtime": {
        "host_preflight": "host-diagnostics",
        "host_verify": "host-diagnostics",
        "host_bootstrap": "host-diagnostics",
        "recovery_bundle": "host-diagnostics",
        "ssh_resolve": "ssh",
        "ssh_host": "ssh",
        "browser_profile_launch": "firefox-browser-profiles",
        "intdata_vault_sanitize": "vault-maintenance",
        "intdata_runtime_vault_gc": "vault-maintenance",
    },
    "intbrain": {
        "intbrain_context_pack": "context-memory",
        "intbrain_memory_search": "context-memory",
        "intbrain_context_store": "context-memory",
        "intbrain_graph_link": "context-memory",
        "intbrain_people_resolve": "people-graph-policies",
        "intbrain_people_get": "people-graph-policies",
        "intbrain_graph_neighbors": "people-graph-policies",
        "intbrain_people_policy_tg_get": "people-graph-policies",
        "intbrain_group_policy_get": "people-graph-policies",
        "intbrain_group_policy_upsert": "people-graph-policies",
        "intbrain_policy_events_list": "people-graph-policies",
        "intbrain_jobs_list": "jobs-runtime",
        "intbrain_jobs_get": "jobs-runtime",
        "intbrain_jobs_sync_runtime": "jobs-runtime",
        "intbrain_job_policy_upsert": "jobs-runtime",
        "intbrain_pm_dashboard": "pm-dashboard-tasks",
        "intbrain_pm_tasks": "pm-dashboard-tasks",
        "intbrain_pm_para": "pm-dashboard-tasks",
        "intbrain_pm_health": "pm-dashboard-tasks",
        "intbrain_pm_constraints_validate": "pm-dashboard-tasks",
        "intbrain_pm_task_create": "pm-dashboard-tasks",
        "intbrain_pm_task_patch": "pm-dashboard-tasks",
        "intbrain_memory_recent_work": "session-memory",
        "intbrain_memory_session_brief": "session-memory",
        "intbrain_memory_sync_sessions": "session-memory",
        "intbrain_import_vault_pm": "external-imports",
        "intbrain_memory_import_mempalace": "external-imports",
    },
    "intdb": {
        "intdata_cli": "doctor-status",
    },
}

REQUIRED_CARD_MARKERS = [
    "Когда:",
    "Required inputs:",
    "Optional/schema inputs:",
    "Режим:",
    "Approval / issue requirements:",
    "Не использовать когда:",
    "Пример вызова:",
    "Fallback/blocker:",
]

GUARDED_TOOLS = {
    "lockctl_acquire", "lockctl_renew", "lockctl_release_path", "lockctl_release_issue", "lockctl_gc",
    "openspec_archive", "openspec_change", "openspec_spec", "openspec_new", "openspec_exec",
    "sync_gate", "publish", "commit_binding",
    "host_bootstrap", "recovery_bundle", "ssh_host", "browser_profile_launch",
    "intdata_vault_sanitize", "intdata_runtime_vault_gc",
    "intbrain_context_store", "intbrain_graph_link", "intbrain_group_policy_upsert", "intbrain_jobs_sync_runtime",
    "intbrain_job_policy_upsert", "intbrain_pm_task_create", "intbrain_pm_task_patch", "intbrain_import_vault_pm",
    "intbrain_memory_sync_sessions", "intbrain_memory_import_mempalace", "intdata_cli",
}

GUARD_WORDS = ["approval", "confirm_mutation", "issue_context", "owner approval"]
READ_ONLY_MARKERS = ["Режим: read-only", "Режим: read-only by default"]
CABINET_RE = re.compile(r"cabinet|intbrain_cabinet", re.IGNORECASE)


def frame(payload: dict[str, Any]) -> bytes:
    raw = json.dumps(payload).encode("utf-8")
    return b"Content-Length: " + str(len(raw)).encode("ascii") + b"\r\n\r\n" + raw


def parse_frames(raw: bytes) -> list[dict[str, Any]]:
    messages = []
    rest = raw
    while rest:
        head, sep, body = rest.partition(b"\r\n\r\n")
        if not sep:
            break
        length = int(head.decode("ascii").split(":", 1)[1].strip())
        messages.append(json.loads(body[:length].decode("utf-8")))
        rest = body[length:]
    return messages


def mcp_exchange(profile: str, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = b"".join(frame(req) for req in requests)
    proc = subprocess.run(
        [sys.executable, str(MCP_SERVER), "--profile", profile],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        timeout=30,
    )
    if proc.returncode != 0:
        raise AssertionError(f"{profile} MCP exited {proc.returncode}: {proc.stderr.decode(errors='replace')}")
    return parse_frames(proc.stdout)


def tools_for(profile: str) -> list[dict[str, Any]]:
    responses = mcp_exchange(
        profile,
        [
            {"id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"id": 2, "method": "ping", "params": {}},
            {"id": 3, "method": "tools/list", "params": {}},
        ],
    )
    by_id = {msg.get("id"): msg for msg in responses}
    if "error" in by_id[1]:
        raise AssertionError(f"{profile} initialize failed: {by_id[1]['error']}")
    if "error" in by_id[2]:
        raise AssertionError(f"{profile} ping failed: {by_id[2]['error']}")
    return by_id[3]["result"]["tools"]


def verify_manifests(report: dict[str, Any]) -> None:
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    for name, plugin_dir in PLUGIN_DIRS.items():
        if name not in entries:
            report["manifest_errors"].append(f"missing marketplace entry: {name}")
            continue
        manifest = json.loads((plugin_dir / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        if manifest.get("name") != name:
            report["manifest_errors"].append(f"manifest name mismatch for {name}")
        for key in ("skills", "mcpServers", "interface"):
            if key not in manifest:
                report["manifest_errors"].append(f"{name} missing {key}")
        interface = manifest.get("interface", {})
        for key in ("displayName", "shortDescription", "longDescription", "defaultPrompt", "brandColor"):
            if key not in interface:
                report["manifest_errors"].append(f"{name} interface missing {key}")
        if name == "intbrain" and CABINET_RE.search(json.dumps(manifest, ensure_ascii=False)):
            report["manifest_errors"].append("intbrain manifest leaks Cabinet active surface")


def extract_card(body: str, tool_name: str) -> str | None:
    marker = f"### {tool_name}"
    start = body.find(marker)
    if start < 0:
        return None
    next_start = body.find("\n### ", start + len(marker))
    return body[start:] if next_start < 0 else body[start:next_start]


def required_args(tool: dict[str, Any]) -> list[str]:
    return list(tool.get("inputSchema", {}).get("required", []) or [])


def verify_skill_card(profile: str, tool: dict[str, Any], report: dict[str, Any]) -> None:
    tool_name = tool["name"]
    skill = TOOL_SKILLS[profile].get(tool_name)
    row = {"profile": profile, "tool": tool_name, "skill": skill, "missing_guidance": []}
    report["matrix"].append(row)
    if not skill:
        row["missing_guidance"].append("no skill mapping")
        return
    path = PLUGIN_DIRS[profile] / "skills" / skill / "SKILL.md"
    if not path.exists():
        row["missing_guidance"].append(f"missing skill file: {path}")
        return
    body = path.read_text(encoding="utf-8")
    card = extract_card(body, tool_name)
    if not card:
        row["missing_guidance"].append("missing tool card heading")
        return
    for marker in REQUIRED_CARD_MARKERS:
        if marker not in card:
            row["missing_guidance"].append(f"missing marker {marker}")
    for arg in required_args(tool):
        if f"`{arg}`" not in card:
            row["missing_guidance"].append(f"required arg not documented: {arg}")
    if tool_name in GUARDED_TOOLS or {"confirm_mutation", "issue_context"} & set(required_args(tool)):
        missing = [word for word in GUARD_WORDS if word not in card]
        if missing:
            row["missing_guidance"].append(f"missing guard wording: {', '.join(missing)}")
    else:
        if not any(marker in card for marker in READ_ONLY_MARKERS):
            row["missing_guidance"].append("missing read-only marker")
    if CABINET_RE.search(tool_name):
        row["missing_guidance"].append("Cabinet tool leaked into active surface")


def verify_skill_coverage(profile: str, tools: list[dict[str, Any]], report: dict[str, Any]) -> None:
    names = {tool["name"] for tool in tools}
    mapping = TOOL_SKILLS[profile]
    missing = sorted(names - set(mapping))
    extra = sorted(set(mapping) - names)
    if missing or extra:
        report["mapping_errors"].append({"profile": profile, "missing": missing, "extra": extra})
    for tool in tools:
        verify_skill_card(profile, tool, report)


def verify_cabinet_absent(report: dict[str, Any]) -> None:
    scan_roots = [
        ROOT / "codex" / "plugins" / "intbrain" / "skills",
        ROOT / "codex" / "plugins" / "intbrain" / ".codex-plugin" / "plugin.json",
    ]
    for root in scan_roots:
        paths = [root] if root.is_file() else list(root.rglob("*.md"))
        for path in paths:
            if CABINET_RE.search(path.read_text(encoding="utf-8")):
                report["cabinet_errors"].append(str(path.relative_to(ROOT)))


def verify_guard_cases(profile: str) -> None:
    guard_cases = {
        "intdata-control": [("openspec_archive", {"change_name": "guard-negative"}), ("publish", {"target": "tools"}), ("commit_binding", {"commit_sha": "0" * 40}), ("multica_issue", {"command": "create", "args": ["guard-negative"]})],
        "intdata-runtime": [("host_bootstrap", {}), ("recovery_bundle", {}), ("browser_profile_launch", {"profile": "firefox-default"}), ("intdata_vault_sanitize", {"dry_run": False})],
        "intbrain": [("intbrain_context_store", {"owner_id": 1, "kind": "note", "title": "guard", "text_content": "guard"}), ("intbrain_pm_task_create", {"owner_id": 1, "title": "guard"}), ("intbrain_jobs_sync_runtime", {"owner_id": 1})],
        "intdb": [("intdata_cli", {"command": "intdb", "args": ["migrate", "apply"]})],
    }
    requests = [{"id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}]
    for idx, (tool, args) in enumerate(guard_cases.get(profile, []), start=2):
        requests.append({"id": idx, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    responses = mcp_exchange(profile, requests)
    for msg in responses:
        if msg.get("id") == 1:
            continue
        text = json.dumps(msg, ensure_ascii=False)
        if "confirm_mutation" not in text and "issue_context" not in text:
            raise AssertionError(f"{profile} guard case did not reject mutation: {text}")


def build_report(skip_guards: bool) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": True,
        "expected_counts": EXPECTED_COUNTS,
        "counts": {},
        "manifest_errors": [],
        "mapping_errors": [],
        "cabinet_errors": [],
        "matrix": [],
    }
    verify_manifests(report)
    for profile, expected in EXPECTED_COUNTS.items():
        tools = tools_for(profile)
        names = {tool["name"] for tool in tools}
        report["counts"][profile] = len(tools)
        if len(tools) != expected:
            report["mapping_errors"].append({"profile": profile, "expected": expected, "actual": len(tools)})
        leaked = sorted(name for name in names if CABINET_RE.search(name))
        if leaked:
            report["cabinet_errors"].append({"profile": profile, "tools": leaked})
        verify_skill_coverage(profile, tools, report)
        if not skip_guards:
            verify_guard_cases(profile)
    verify_cabinet_absent(report)
    missing_count = sum(len(row["missing_guidance"]) for row in report["matrix"])
    report["missing_guidance_count"] = missing_count
    report["ok"] = not (report["manifest_errors"] or report["mapping_errors"] or report["cabinet_errors"] or missing_count)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-guards", action="store_true")
    parser.add_argument("--report-json", action="store_true")
    args = parser.parse_args()

    report = build_report(skip_guards=args.skip_guards)
    if args.report_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for row in report["matrix"]:
            status = "ok" if not row["missing_guidance"] else "; ".join(row["missing_guidance"])
            print(f"{row['profile']}/{row['tool']} -> {row['skill']} -> {status}")
        if report["ok"]:
            print("ok: int-tools plugin manifests, MCP smoke, skill cards, Cabinet exclusion, and guard checks passed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
