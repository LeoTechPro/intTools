#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Sequence


DBA_ROOT = Path(__file__).resolve().parents[1]
DBA_PY = DBA_ROOT / "lib" / "dba.py"


@dataclass(frozen=True)
class EntryPointConfig:
    profile: str
    role: str
    database: str
    environment: str


class WrapperError(RuntimeError):
    pass


def _print_banner(config: EntryPointConfig, mode: str) -> None:
    line = "=" * 42
    print(line)
    print(f"YOU ARE CONNECTING TO {config.environment.upper()}")
    print(f"ROLE = {config.role}")
    print(f"DB   = {config.database}")
    print(f"MODE = {mode}")
    print(line)


def _run_dba(args: Sequence[str]) -> int:
    if not DBA_PY.exists():
        raise WrapperError(f"intDBA core not found: {DBA_PY}")
    command = [sys.executable, str(DBA_PY), *args]
    return subprocess.call(command)


def _require_confirmation(actual: str, expected: str, flag_name: str = "--confirm-target") -> None:
    if actual != expected:
        raise WrapperError(f"Set {flag_name} {expected} to continue.")


def readonly_main(config: EntryPointConfig) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql")
    parser.add_argument("--path")
    parser.add_argument("--doctor", action="store_true")
    args = parser.parse_args()

    if sum(bool(value) for value in (args.sql, args.path, args.doctor)) != 1:
        raise WrapperError("Use exactly one of --doctor, --sql, or --path.")

    _print_banner(config, "READONLY")
    if args.doctor:
        return _run_dba(["doctor", "--profile", config.profile])
    if args.sql:
        return _run_dba(["sql", "--profile", config.profile, "--sql", args.sql])
    return _run_dba(["file", "--profile", config.profile, "--path", args.path])


def migrate_main(config: EntryPointConfig, *, prod: bool) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path")
    parser.add_argument("--mode", choices=("incremental", "bootstrap"), default="incremental")
    parser.add_argument("--repo")
    parser.add_argument("--seed-business", action="store_true")
    parser.add_argument("--write", action="store_true", required=True)
    parser.add_argument("--confirm-target", required=True)
    parser.add_argument("--prod", action="store_true", required=prod)
    args = parser.parse_args()

    if bool(args.path) and args.seed_business:
        raise WrapperError("--seed-business is only valid for migrate data mode.")
    if not args.path and args.mode not in ("incremental", "bootstrap"):
        raise WrapperError("Unsupported migrate mode.")
    if prod and not args.prod:
        raise WrapperError("This entrypoint requires --prod.")
    _require_confirmation(args.confirm_target, config.database)

    _print_banner(config, "WRITE (MIGRATION)")
    if args.path:
        command = [
            "file",
            "--profile",
            config.profile,
            "--path",
            args.path,
            "--write",
            "--approve-target",
            config.profile,
        ]
        if prod:
            command.append("--force-prod-write")
        return _run_dba(command)

    command = [
        "migrate",
        "data",
        "--target",
        config.profile,
        "--mode",
        args.mode,
        "--approve-target",
        config.profile,
    ]
    if args.repo:
        command.extend(["--repo", args.repo])
    if args.seed_business:
        command.append("--seed-business")
    if prod:
        command.append("--force-prod-write")
    return _run_dba(command)


def admin_main(config: EntryPointConfig, *, prod: bool) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql")
    parser.add_argument("--path")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--breakglass")
    args = parser.parse_args()

    if sum(bool(value) for value in (args.sql, args.path, args.doctor)) != 1:
        raise WrapperError("Use exactly one of --doctor, --sql, or --path.")
    if args.breakglass != "I_UNDERSTAND_BREAKGLASS":
        raise WrapperError("Set --breakglass I_UNDERSTAND_BREAKGLASS to continue.")

    _print_banner(config, "BREAKGLASS ADMIN")
    if args.doctor:
        return _run_dba(["doctor", "--profile", config.profile])
    command = [
        "sql" if args.sql else "file",
        "--profile",
        config.profile,
        "--sql" if args.sql else "--path",
        args.sql or args.path,
        "--write",
        "--approve-target",
        config.profile,
    ]
    if prod:
        command.append("--force-prod-write")
    return _run_dba(command)


def test_bootstrap_main(config: EntryPointConfig) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--confirm-target")
    args = parser.parse_args()

    if args.doctor and args.path:
        raise WrapperError("Use either --doctor or --path.")
    if not args.doctor and not args.path:
        raise WrapperError("Use either --doctor or --path.")

    _print_banner(config, "DISPOSABLE TEST BOOTSTRAP")
    if args.doctor:
        return _run_dba(["doctor", "--profile", config.profile])

    if not args.write:
        raise WrapperError("This entrypoint requires --write for mutating operations.")
    _require_confirmation(args.confirm_target or "", config.database)
    return _run_dba(
        [
            "file",
            "--profile",
            config.profile,
            "--path",
            args.path,
            "--write",
            "--approve-target",
            config.profile,
        ]
    )


def main(config: EntryPointConfig, mode: str, *, prod: bool = False) -> int:
    try:
        if mode == "readonly":
            return readonly_main(config)
        if mode == "migrate":
            return migrate_main(config, prod=prod)
        if mode == "admin":
            return admin_main(config, prod=prod)
        if mode == "test-bootstrap":
            return test_bootstrap_main(config)
        raise WrapperError(f"Unsupported wrapper mode: {mode}")
    except WrapperError as exc:
        print(exc, file=sys.stderr)
        return 2
