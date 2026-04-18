#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
import os
import sys
import tomllib
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
    return (resolve_int_root() / ".runtime").resolve()


def default_cloud_root() -> Path:
    explicit = os.environ.get("CLOUD_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (resolve_int_root() / "cloud").resolve()


def top_level_entries(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {entry.name for entry in path.iterdir()}


def matches_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


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
    config_data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    mcp_servers = config_data.get("mcp_servers", {})
    tools_root = REPO_ROOT.resolve().as_posix()
    cloud_root = default_cloud_root().as_posix()

    if config_data.get("default_cwd") != resolve_int_root().as_posix():
        issues.append(f"config.toml default_cwd mismatch: {config_data.get('default_cwd')!r}")

    filesystem_args = mcp_servers.get("filesystem", {}).get("args", [])
    if CODEX_HOME.as_posix() not in filesystem_args:
        issues.append(f"filesystem MCP args missing CODEX_HOME path: {CODEX_HOME.as_posix()}")

    for server_name, expected_path in {
        "gdrive_fs": f"{cloud_root}/gdrive",
        "yadisk_fs": f"{cloud_root}/yadisk",
    }.items():
        if expected_path not in mcp_servers.get(server_name, {}).get("args", []):
            issues.append(f"{server_name} args missing expected path: {expected_path}")

    if current_platform() == "windows":
        expected_servers = {
            "github": ("bash", [f"{tools_root}/codex/bin/mcp-github-from-gh.sh"]),
            "postgres": ("bash", [f"{tools_root}/codex/bin/mcp-postgres-from-backend-env.sh"]),
            "obsidian_memory": ("bash", [f"{tools_root}/codex/bin/mcp-obsidian-memory.sh"]),
            "bitrix24": ("bash", [f"{tools_root}/codex/bin/mcp-bitrix24.sh"]),
            "lockctl": ("python", [f"{tools_root}/codex/bin/mcp-lockctl.py"]),
        }
    else:
        expected_servers = {
            "github": (f"{tools_root}/codex/bin/mcp-github-from-gh.sh", []),
            "postgres": (f"{tools_root}/codex/bin/mcp-postgres-from-backend-env.sh", []),
            "obsidian_memory": (f"{tools_root}/codex/bin/mcp-obsidian-memory.sh", []),
            "bitrix24": (f"{tools_root}/codex/bin/mcp-bitrix24.sh", []),
            "lockctl": (f"{tools_root}/codex/bin/mcp-lockctl.sh", []),
        }

    for server_name, (expected_command, expected_args) in expected_servers.items():
        server = mcp_servers.get(server_name, {})
        if server.get("command") != expected_command:
            issues.append(
                f"config.toml {server_name} command mismatch: {server.get('command')!r} != {expected_command!r}"
            )
        if server.get("args", []) != expected_args:
            issues.append(
                f"config.toml {server_name} args mismatch: {server.get('args', [])!r} != {expected_args!r}"
            )


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
