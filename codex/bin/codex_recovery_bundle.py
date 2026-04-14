#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tool_routing import assert_binding  # noqa: E402


PASS_ENV_VAR = "CODEX_RECOVERY_PASSPHRASE"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export/import encrypted Codex recovery bundles")
    parser.add_argument("--binding-origin", default="codex/bin/codex_recovery_bundle.py")
    parser.add_argument("command", choices=("export", "import"))
    parser.add_argument("bundle_path")
    return parser


def ensure_passphrase() -> str:
    value = os.environ.get(PASS_ENV_VAR, "")
    if value:
        return value
    value = getpass.getpass("Recovery bundle passphrase: ")
    os.environ[PASS_ENV_VAR] = value
    return value


def merge_copy(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


def resolve_openssl() -> str:
    resolved = shutil.which("openssl")
    if resolved:
        return resolved
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "")) / "Git/usr/bin/openssl.exe",
            Path(os.environ.get("ProgramFiles", "")) / "OpenSSL-Win64/bin/openssl.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "OpenSSL-Win32/bin/openssl.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
    raise RuntimeError("openssl executable was not found in PATH")


def export_bundle(bundle_path: Path) -> None:
    runtime_root = Path(os.environ.get("CODEX_RUNTIME_ROOT", "/int/.runtime")).expanduser()
    secrets_root = Path(os.environ.get("CODEX_SECRETS_ROOT", runtime_root / "codex-secrets")).expanduser()
    cloud_access_root = Path(os.environ.get("CLOUD_ACCESS_ROOT", runtime_root / "cloud-access")).expanduser()
    openclaw_secrets_root = Path(os.environ.get("OPENCLAW_SECRETS_ROOT", Path.home() / ".openclaw" / "secrets")).expanduser()

    with tempfile.TemporaryDirectory() as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        (temp_dir / "int/.runtime").mkdir(parents=True, exist_ok=True)
        (temp_dir / "home/.openclaw").mkdir(parents=True, exist_ok=True)
        merge_copy(secrets_root, temp_dir / "int/.runtime/codex-secrets")
        cloud_config = cloud_access_root / "rclone.conf"
        if cloud_config.exists():
            merge_copy(cloud_config.parent, temp_dir / "int/.runtime/cloud-access")
        merge_copy(openclaw_secrets_root, temp_dir / "home/.openclaw/secrets")
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "paths": [
                        "/int/.runtime/codex-secrets/",
                        "/int/.runtime/cloud-access/rclone.conf",
                        "~/.openclaw/secrets/",
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        archive_path = temp_dir / "recovery.tgz"
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(temp_dir / "int", arcname="int")
            archive.add(temp_dir / "home", arcname="home")
            archive.add(manifest_path, arcname="manifest.json")

        openssl = resolve_openssl()
        run_checked(
            [
                openssl,
                "enc",
                "-aes-256-cbc",
                "-pbkdf2",
                "-salt",
                "-pass",
                f"env:{PASS_ENV_VAR}",
                "-in",
                str(archive_path),
                "-out",
                str(bundle_path),
            ]
        )
    print(f"exported recovery bundle to {bundle_path}")


def import_bundle(bundle_path: Path) -> None:
    runtime_root = Path(os.environ.get("CODEX_RUNTIME_ROOT", "/int/.runtime")).expanduser()
    secrets_root = Path(os.environ.get("CODEX_SECRETS_ROOT", runtime_root / "codex-secrets")).expanduser()
    cloud_access_root = Path(os.environ.get("CLOUD_ACCESS_ROOT", runtime_root / "cloud-access")).expanduser()
    openclaw_secrets_root = Path(os.environ.get("OPENCLAW_SECRETS_ROOT", Path.home() / ".openclaw" / "secrets")).expanduser()

    with tempfile.TemporaryDirectory() as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        archive_path = temp_dir / "recovery.tgz"
        openssl = resolve_openssl()
        run_checked(
            [
                openssl,
                "enc",
                "-d",
                "-aes-256-cbc",
                "-pbkdf2",
                "-pass",
                f"env:{PASS_ENV_VAR}",
                "-in",
                str(bundle_path),
                "-out",
                str(archive_path),
            ]
        )
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(temp_dir)

        secrets_root.mkdir(parents=True, exist_ok=True)
        openclaw_secrets_root.mkdir(parents=True, exist_ok=True)
        merge_copy(temp_dir / "int/.runtime/codex-secrets", secrets_root)
        cloud_config = temp_dir / "int/.runtime/cloud-access"
        if cloud_config.exists():
            cloud_access_root.mkdir(parents=True, exist_ok=True)
            merge_copy(cloud_config, cloud_access_root)
        merge_copy(temp_dir / "home/.openclaw/secrets", openclaw_secrets_root)
    print(f"imported recovery bundle from {bundle_path}")


def main() -> int:
    args = build_parser().parse_args()
    assert_binding("codex-recovery-bundle", args.binding_origin)
    ensure_passphrase()
    bundle_path = Path(args.bundle_path).expanduser().resolve()
    if args.command == "export":
        export_bundle(bundle_path)
    else:
        import_bundle(bundle_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
