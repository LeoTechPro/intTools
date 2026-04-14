#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tool_routing import assert_binding  # noqa: E402


PACKAGE_SPEC = "firefox-devtools-mcp@0.9.1"


def runtime_root() -> Path:
    for candidate in (Path("/int/.runtime/firefox-mcp"), Path("D:/int/.runtime/firefox-mcp")):
        if candidate.exists():
            return candidate.resolve()
    return Path("D:/int/.runtime/firefox-mcp").resolve() if os.name == "nt" else Path("/int/.runtime/firefox-mcp").resolve()


def normalize_cli_args(argv: list[str]) -> list[str]:
    switch_map = {
        "visible": "--visible",
        "dryrun": "--dry-run",
    }
    value_map = {
        "profilekey": "--profile-key",
        "starturl": "--start-url",
        "viewport": "--viewport",
        "capability": "--capability",
        "bindingorigin": "--binding-origin",
    }

    def normalize_key(raw: str) -> str:
        return raw.strip().lower().replace("-", "").replace("_", "")

    normalized: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if not token.startswith("-") or token.startswith("--"):
            normalized.append(token)
            index += 1
            continue
        key = normalize_key(token[1:])
        if key in switch_map:
            normalized.append(switch_map[key])
            index += 1
            continue
        if key in value_map:
            normalized.append(value_map[key])
            if index + 1 < len(argv):
                normalized.append(argv[index + 1])
                index += 2
            else:
                index += 1
            continue
        normalized.append(token)
        index += 1
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Platform-neutral Firefox MCP launcher for Codex overlays")
    parser.add_argument("--capability", required=True)
    parser.add_argument("--binding-origin", default="codex/bin/firefox_mcp_launcher.py")
    parser.add_argument("--profile-key", required=True)
    parser.add_argument("--start-url", required=True)
    parser.add_argument("--viewport", default="1440x900")
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def resolve_command(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    raise RuntimeError(f"required tool '{name}' was not found in PATH")


def resolve_firefox_binary() -> str:
    for candidate in ("firefox.exe", "firefox"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "")) / "Mozilla Firefox/firefox.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Mozilla Firefox/firefox.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
    raise RuntimeError("Firefox executable was not found. Install Firefox 100+ or add it to PATH.")


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def remove_stale_run_meta(run_meta_path: Path, profile_key: str) -> None:
    if not run_meta_path.exists():
        return
    try:
        raw = json.loads(run_meta_path.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    existing_pid = int(raw.get("pid", 0) or 0)
    if existing_pid > 0 and pid_alive(existing_pid):
        raise RuntimeError(f"Firefox MCP profile '{profile_key}' is already active under PID {existing_pid}.")
    run_meta_path.unlink(missing_ok=True)


def main() -> int:
    args = build_parser().parse_args(normalize_cli_args(sys.argv[1:]))
    assert_binding(args.capability, args.binding_origin)

    root = runtime_root()
    profiles_root = root / "profiles"
    logs_root = root / "logs"
    run_root = root / "run"
    profile_path = profiles_root / args.profile_key
    log_dir = logs_root / args.profile_key
    run_meta_path = run_root / f"{args.profile_key}.json"
    stderr_log_path = log_dir / "stderr.log"

    ensure_directory(profiles_root)
    ensure_directory(logs_root)
    ensure_directory(run_root)
    ensure_directory(profile_path)
    ensure_directory(log_dir)
    remove_stale_run_meta(run_meta_path, args.profile_key)

    npx_path = resolve_command("npx")
    firefox_path = resolve_firefox_binary()

    command = [
        npx_path,
        "-y",
        PACKAGE_SPEC,
        "--firefox-path",
        firefox_path,
        "--profile-path",
        str(profile_path),
        "--start-url",
        args.start_url,
        "--viewport",
        args.viewport,
    ]
    if not args.visible:
        command.append("--headless")

    meta = {
        "capability": args.capability,
        "profile_key": args.profile_key,
        "start_url": args.start_url,
        "viewport": args.viewport,
        "visible": bool(args.visible),
        "profile_path": str(profile_path),
        "log_path": str(stderr_log_path),
        "package": PACKAGE_SPEC,
        "command": command,
    }
    if args.dry_run:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    with stderr_log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(command, stderr=log_file)
        run_meta_path.write_text(
            json.dumps(
                {
                    **meta,
                    "pid": process.pid,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            return process.wait()
        finally:
            run_meta_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
