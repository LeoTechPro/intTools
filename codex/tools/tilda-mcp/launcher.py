from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys


ALLOWED_KEYS = {"TILDA_PUBLIC_KEY", "TILDA_SECRET_KEY", "TILDA_PROJECT_ID"}
REQUIRED_KEYS = {"TILDA_PUBLIC_KEY", "TILDA_SECRET_KEY"}


class LauncherError(RuntimeError):
    pass


def default_secret_file() -> Path:
    pointer = os.environ.get("TILDA_SECRET_FILE")
    if pointer:
        return Path(pointer).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "intdata" / "secrets" / "punkt-b" / "tilda.env"
    return Path("/home/agents/.hermes/secrets/punkt-b/tilda/secrets.env")


def _check_permissions(path: Path) -> None:
    if os.name == "nt":
        return
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise LauncherError(f"Secret file permissions must be 0600 or stricter: {path}")


def load_secret_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise LauncherError(f"Protected Tilda secret file is missing: {path}")
    _check_permissions(path)
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise LauncherError(f"Invalid secret-file line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_KEYS:
            raise LauncherError(f"Unsupported variable in secret file: {key}")
        if not value:
            raise LauncherError(f"Empty value for {key}")
        values[key] = value
    missing = sorted(REQUIRED_KEYS - values.keys())
    if missing:
        raise LauncherError(f"Missing required variables: {', '.join(missing)}")
    return values


def build_environment(secret_file: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(load_secret_file(secret_file))
    root = Path(__file__).resolve().parent
    tools_root = root.parents[2]
    candidates = [
        tools_root / ".runtime" / "tilda-mcp" / ".deps",
        root / ".deps",
    ]
    python_paths = [str(path) for path in candidates if path.is_dir()]
    python_paths.append(str(root))
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    return environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Secret-safe Tilda MCP launcher")
    parser.add_argument("--secret-file", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    secret_file = args.secret_file or default_secret_file()
    try:
        environment = build_environment(secret_file)
    except LauncherError as exc:
        print(f"tilda launcher error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if args.check:
        print("tilda launcher: configuration valid")
        return
    os.execvpe(
        sys.executable,
        [sys.executable, "-m", "tilda_mcp.server"],
        environment,
    )


if __name__ == "__main__":
    main()
