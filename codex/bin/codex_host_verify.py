#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tool_routing import assert_binding  # noqa: E402


ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT_DIR.parent
POLICY_PATH = ROOT_DIR / "layout-policy.json"


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def current_platform() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def resolve_int_root() -> Path:
    explicit = os.environ.get("INT_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    for parent in REPO_ROOT.resolve().parents:
        if parent.name.lower() == "int":
            return parent.resolve()

    candidates = (Path("D:/int"), Path("/int")) if current_platform() == "windows" else (Path("/int"), Path("D:/int"))
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def default_runtime_root() -> Path:
    explicit = os.environ.get("CODEX_RUNTIME_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (REPO_ROOT / ".runtime").resolve()


def default_cloud_root() -> Path:
    explicit = os.environ.get("CLOUD_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (resolve_int_root() / "cloud").resolve()


def main() -> int:
    binding_origin = "codex/bin/codex_host_verify.py"
    if len(sys.argv) > 2 and sys.argv[1] == "--binding-origin":
        binding_origin = sys.argv[2]
        del sys.argv[1:3]
    assert_binding("codex-host-verify", binding_origin)

    policy = load_policy()
    issues: list[str] = []

    for path_str in policy["required_repo_paths"]:
        resolved = (REPO_ROOT / path_str).resolve()
        if not resolved.exists():
            issues.append(f"missing repo path: {resolved}")

    for path_str in policy["required_runtime_dirs"]:
        resolved = (default_runtime_root() / path_str).resolve()
        if not resolved.exists():
            issues.append(f"missing runtime path: {resolved}")

    for path_str in policy.get("required_cloud_dirs", []):
        resolved = (default_cloud_root() / path_str).resolve()
        if not resolved.exists():
            issues.append(f"missing cloud path: {resolved}")

    if issues:
        print("codex host verify: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("codex host verify: ok")
    print("- codex home: not inspected; native Codex owns this state")
    print(f"- policy: {POLICY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
