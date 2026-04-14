#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
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
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def current_platform() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def normalize_text(value: str) -> str:
    return value.replace("\\", "/")


def tools_root_candidates() -> list[Path]:
    candidates = [REPO_ROOT]
    for raw in (os.environ.get("INT_TOOLS_ROOT", ""), "/int/tools", "D:/int/tools"):
        if raw:
            candidates.append(Path(raw).expanduser())
    seen: set[str] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        key = normalize_text(str(candidate.resolve() if candidate.exists() else candidate))
        if key not in seen:
            seen.add(key)
            ordered.append(candidate)
    return ordered


def int_root_candidates() -> list[Path]:
    explicit_runtime = os.environ.get("CODEX_RUNTIME_ROOT", "").strip()
    candidates = [Path("/int"), Path("D:/int")]
    if explicit_runtime:
        candidates.insert(0, Path(explicit_runtime).expanduser().parent)
    return candidates


def remap_canonical_path(path_str: str) -> Path:
    normalized = normalize_text(path_str)
    if normalized.startswith("/int/tools/") or normalized.startswith("D:/int/tools/"):
        rel = normalized.split("/int/tools/", 1)[1] if "/int/tools/" in normalized else normalized.split("D:/int/tools/", 1)[1]
        return (REPO_ROOT / rel.replace("/", os.sep)).resolve()
    if normalized.startswith("/int/.runtime/") or normalized.startswith("D:/int/.runtime/"):
        rel = normalized.split("/int/.runtime/", 1)[1] if "/int/.runtime/" in normalized else normalized.split("D:/int/.runtime/", 1)[1]
        runtime_root = Path(os.environ.get("CODEX_RUNTIME_ROOT", "D:/int/.runtime" if current_platform() == "windows" else "/int/.runtime"))
        return (runtime_root.expanduser() / rel.replace("/", os.sep)).resolve()
    if normalized.startswith("/int/cloud/") or normalized.startswith("D:/int/cloud/"):
        rel = normalized.split("/int/cloud/", 1)[1] if "/int/cloud/" in normalized else normalized.split("D:/int/cloud/", 1)[1]
        int_root = Path("D:/int" if current_platform() == "windows" else "/int")
        return (int_root / "cloud" / rel.replace("/", os.sep)).resolve()
    return Path(path_str).expanduser().resolve()


def top_level_entries(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {entry.name for entry in path.iterdir()}


def matches_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def collect_missing_config_fragments(config_text: str, codex_home: Path = CODEX_HOME) -> list[str]:
    normalized = normalize_text(config_text)
    missing: list[str] = []

    repo_rel_paths = [
        "codex/bin/mcp-github-from-gh.sh",
        "codex/bin/mcp-postgres-from-backend-env.sh",
        "codex/bin/mcp-obsidian-memory.sh",
        "codex/bin/mcp-timeweb.sh",
        "codex/bin/mcp-timeweb-readonly.sh",
        "codex/bin/mcp-bitrix24.sh",
    ]

    required_candidates: dict[str, list[str]] = {}
    for rel in repo_rel_paths:
        required_candidates[rel] = [normalize_text(str(root / rel.replace("/", os.sep))) for root in tools_root_candidates()]

    required_candidates["/int/cloud/gdrive"] = [normalize_text(str(root / "cloud" / "gdrive")) for root in int_root_candidates()]
    required_candidates["/int/cloud/yadisk"] = [normalize_text(str(root / "cloud" / "yadisk")) for root in int_root_candidates()]
    required_candidates[str(codex_home)] = [normalize_text(str(codex_home))]

    for label, candidates in required_candidates.items():
        if not any(candidate in normalized for candidate in candidates):
            missing.append(label)

    if all(fragment not in normalized for fragment in ("lockctl-mcp", "lockctl-mcp.cmd", "lockctl-mcp.sh")):
        missing.append("lockctl MCP command fragment: lockctl-mcp or lockctl-mcp.cmd")

    return missing


def compare_project_overlays(issues: list[str]) -> None:
    tracked_root = ROOT_DIR / "projects"
    runtime_root = CODEX_HOME / "projects"
    if not tracked_root.exists():
        return
    tracked_files = sorted(
        str(path.relative_to(tracked_root))
        for path in tracked_root.rglob("*")
        if path.is_file()
    )
    runtime_files = sorted(
        str(path.relative_to(runtime_root))
        for path in runtime_root.rglob("*")
        if path.is_file()
    ) if runtime_root.exists() else []
    missing = [name for name in tracked_files if name not in runtime_files]
    extra = [name for name in runtime_files if name not in tracked_files]
    if missing:
        issues.append(f"runtime projects missing tracked files: {', '.join(missing)}")
    if extra:
        issues.append(f"runtime projects contain unexpected files: {', '.join(extra)}")


def verify_config(issues: list[str]) -> None:
    config_path = CODEX_HOME / "config.toml"
    if not config_path.exists():
        issues.append(f"missing config file: {config_path}")
        return
    config_text = config_path.read_text(encoding="utf-8")
    for fragment in collect_missing_config_fragments(config_text, CODEX_HOME):
        issues.append(f"config.toml missing fragment: {fragment}")


def main() -> int:
    binding_origin = "codex/bin/codex_host_verify.py"
    if len(sys.argv) > 2 and sys.argv[1] == "--binding-origin":
        binding_origin = sys.argv[2]
        del sys.argv[1:3]
    assert_binding("codex-host-verify", binding_origin)

    policy = load_policy()
    issues: list[str] = []

    actual_roots = top_level_entries(CODEX_HOME)
    allowed_roots = set(policy["home_managed_roots"]) | set(policy["home_runtime_roots"])
    forbidden_roots = set(policy["home_forbidden_roots"])
    forbidden_globs = list(policy["home_forbidden_globs"])

    for name in sorted(actual_roots):
        if name in forbidden_roots or matches_any(name, forbidden_globs):
            issues.append(f"forbidden path present in {CODEX_HOME}: {name}")
        elif name not in allowed_roots:
            issues.append(f"unexpected top-level path in {CODEX_HOME}: {name}")

    for path_str in policy["required_repo_paths"]:
        if not remap_canonical_path(path_str).exists():
            issues.append(f"missing repo path: {path_str}")

    for path_str in policy["required_runtime_dirs"]:
        if not remap_canonical_path(path_str).exists():
            issues.append(f"missing runtime path: {path_str}")

    verify_config(issues)
    compare_project_overlays(issues)

    if issues:
        print("codex host verify: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("codex host verify: ok")
    print(f"- codex home: {CODEX_HOME}")
    print(f"- policy: {POLICY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
