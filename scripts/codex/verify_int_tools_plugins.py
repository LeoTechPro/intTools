#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER = ROOT / "codex" / "bin" / "mcp-intdata-cli.py"

EXPECTED_COUNTS = {
    "intbrain": 29,
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
        "multica_issue": "multica",
        "multica_project": "multica",
        "multica_agent": "multica",
        "multica_workspace": "multica",
        "multica_repo": "multica",
        "multica_skill": "multica",
        "multica_runtime": "multica",
        "multica_daemon": "multica",
        "multica_attachment": "multica",
        "multica_auth": "multica",
        "multica_config": "multica",
        "multica_exec": "multica",
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
        "intbrain_jobs_list": "jobs-pm",
        "intbrain_jobs_get": "jobs-pm",
        "intbrain_jobs_sync_runtime": "jobs-pm",
        "intbrain_job_policy_upsert": "jobs-pm",
        "intbrain_pm_dashboard": "jobs-pm",
        "intbrain_pm_tasks": "jobs-pm",
        "intbrain_pm_para": "jobs-pm",
        "intbrain_pm_health": "jobs-pm",
        "intbrain_pm_constraints_validate": "jobs-pm",
        "intbrain_pm_task_create": "jobs-pm",
        "intbrain_pm_task_patch": "jobs-pm",
        "intbrain_import_vault_pm": "memory-imports",
        "intbrain_memory_recent_work": "memory-imports",
        "intbrain_memory_session_brief": "memory-imports",
        "intbrain_memory_sync_sessions": "memory-imports",
        "intbrain_memory_import_mempalace": "memory-imports",
        "intbrain_cabinet_inventory": "cabinet-absorption",
        "intbrain_cabinet_import": "cabinet-absorption",
    },
    "intdb": {
        "intdata_cli": "doctor-status",
    },
}

GUARD_CASES = {
    "intdata-control": [
        ("openspec_archive", {"change_name": "guard-negative"}),
        ("publish", {"target": "tools"}),
        ("commit_binding", {"commit_sha": "0" * 40}),
        ("multica_issue", {"command": "create", "args": ["guard-negative"]}),
    ],
    "intdata-runtime": [
        ("host_bootstrap", {}),
        ("recovery_bundle", {}),
        ("browser_profile_launch", {"profile": "firefox-default"}),
        ("intdata_vault_sanitize", {"dry_run": False}),
    ],
    "intbrain": [
        ("intbrain_context_store", {"owner_id": 1, "kind": "note", "title": "guard", "text_content": "guard"}),
        ("intbrain_pm_task_create", {"owner_id": 1, "title": "guard"}),
        ("intbrain_jobs_sync_runtime", {"owner_id": 1}),
        ("intbrain_cabinet_import", {"dry_run": False, "owner_id": 1}),
    ],
    "intdb": [
        ("intdata_cli", {"command": "intdb", "args": ["migrate", "apply"]}),
    ],
}


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


def verify_manifests() -> None:
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    for name, plugin_dir in PLUGIN_DIRS.items():
        if name not in entries:
            raise AssertionError(f"missing marketplace entry: {name}")
        manifest = json.loads((plugin_dir / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        if manifest["name"] != name:
            raise AssertionError(f"manifest name mismatch for {name}")
        for key in ("skills", "mcpServers", "interface"):
            if key not in manifest:
                raise AssertionError(f"{name} missing {key}")
        interface = manifest["interface"]
        for key in ("displayName", "shortDescription", "defaultPrompt", "brandColor"):
            if key not in interface:
                raise AssertionError(f"{name} interface missing {key}")


def verify_skill_coverage(profile: str, tool_names: set[str]) -> None:
    mapping = TOOL_SKILLS[profile]
    missing = sorted(tool_names - set(mapping))
    extra = sorted(set(mapping) - tool_names)
    if missing or extra:
        raise AssertionError(f"{profile} skill map mismatch: missing={missing} extra={extra}")
    for tool, skill in mapping.items():
        path = PLUGIN_DIRS[profile] / "skills" / skill / "SKILL.md"
        if not path.exists():
            raise AssertionError(f"{profile}:{tool} skill file missing: {path}")
        body = path.read_text(encoding="utf-8")
        if tool not in body:
            raise AssertionError(f"{profile}:{tool} not mentioned in {path}")


def verify_guard_cases(profile: str) -> None:
    requests = [{"id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}]
    for idx, (tool, args) in enumerate(GUARD_CASES.get(profile, []), start=2):
        requests.append({"id": idx, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    responses = mcp_exchange(profile, requests)
    for msg in responses:
        if msg.get("id") == 1:
            continue
        text = json.dumps(msg, ensure_ascii=False)
        if "confirm_mutation" not in text and "issue_context" not in text:
            raise AssertionError(f"{profile} guard case did not reject mutation: {text}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-guards", action="store_true")
    args = parser.parse_args()

    verify_manifests()
    for profile, expected in EXPECTED_COUNTS.items():
        tools = tools_for(profile)
        names = {tool["name"] for tool in tools}
        if len(tools) != expected:
            raise AssertionError(f"{profile} expected {expected} tools, got {len(tools)}")
        verify_skill_coverage(profile, names)
        if not args.skip_guards:
            verify_guard_cases(profile)

    print("ok: int-tools plugin manifests, MCP smoke, skill coverage, and guard checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
