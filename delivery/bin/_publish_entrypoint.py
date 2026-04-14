#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


INT_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = INT_ROOT / "tools"
PUBLISH_ENGINE = TOOLS_ROOT / "delivery" / "bin" / "publish_repo.py"
ROUTER_ROOT = TOOLS_ROOT / "codex" / "bin"

if str(ROUTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ROUTER_ROOT))

from agent_tool_routing import assert_binding  # noqa: E402


PUBLISH_CONFIGS: dict[str, dict[str, object]] = {
    "publish_data": {
        "repo_path": INT_ROOT / "data",
        "repo_name": "data",
        "success_label": "publish_data",
        "expected_branch": "main",
        "expected_upstream": "origin/main",
        "push_remote": "origin",
        "push_branch": "main",
        "require_clean": True,
        "deploy_mode": "ssh-fast-forward",
        "deploy_host": "vds-intdata-intdata",
        "deploy_repo_path": "/int/data",
        "deploy_fetch_ref": "main",
        "deploy_pull_ref": "main",
    },
    "publish_assess": {
        "repo_path": INT_ROOT / "assess",
        "repo_name": "assess",
        "success_label": "publish_assess",
        "expected_branch": "dev",
        "expected_upstream": "origin/dev",
        "push_remote": "origin",
        "push_branch": "dev",
        "require_clean": True,
        "deploy_mode": "ssh-fast-forward",
        "deploy_host": "vds-intdata-intdata",
        "deploy_repo_path": "/int/assess",
        "deploy_fetch_ref": "dev",
        "deploy_pull_ref": "dev",
    },
    "publish_crm": {
        "repo_path": INT_ROOT / "crm",
        "repo_name": "crm",
        "success_label": "publish_crm",
        "expected_branch": "dev",
        "expected_upstream": "origin/dev",
        "push_remote": "origin",
        "push_branch": "dev",
        "require_clean": True,
    },
    "publish_id": {
        "repo_path": INT_ROOT / "id",
        "repo_name": "id",
        "success_label": "publish_id",
        "expected_branch": "dev",
        "expected_upstream": "origin/dev",
        "push_remote": "origin",
        "push_branch": "dev",
        "require_clean": True,
    },
    "publish_nexus": {
        "repo_path": INT_ROOT / "nexus",
        "repo_name": "nexus",
        "success_label": "publish_nexus",
        "expected_branch": "dev",
        "expected_upstream": "origin/dev",
        "push_remote": "origin",
        "push_branch": "dev",
        "require_clean": True,
    },
    "publish_brain_dev": {
        "repo_path": INT_ROOT / "brain",
        "repo_name": "brain",
        "success_label": "publish_brain_dev",
        "expected_branch": "dev",
        "expected_upstream": "origin/dev",
        "push_remote": "origin",
        "push_branch": "dev",
        "require_clean": True,
        "deploy_mode": "ssh-fast-forward",
        "deploy_host": "vds-intdata-intdata",
        "deploy_repo_path": "/int/brain",
        "deploy_fetch_ref": "dev",
        "deploy_pull_ref": "dev",
    },
}


def build_common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--no-deploy", action="store_true")
    parser.add_argument("--binding-origin", default="")
    return parser


def default_binding_origin(script_name: str) -> str:
    return f"delivery/bin/{script_name}"


def validate_binding(capability_id: str, binding_origin: str) -> None:
    assert_binding(capability_id, binding_origin)


def run_publish_engine(capability_id: str, argv: list[str], script_name: str) -> int:
    parser = build_common_parser()
    args = parser.parse_args(argv)
    binding_origin = args.binding_origin or default_binding_origin(script_name)
    validate_binding(capability_id, binding_origin)

    config = PUBLISH_CONFIGS[capability_id]
    command = [
        sys.executable,
        str(PUBLISH_ENGINE),
        "--repo-path",
        str(config["repo_path"]),
        "--repo-name",
        str(config["repo_name"]),
        "--success-label",
        str(config["success_label"]),
        "--expected-branch",
        str(config["expected_branch"]),
        "--expected-upstream",
        str(config["expected_upstream"]),
        "--push-remote",
        str(config["push_remote"]),
        "--push-branch",
        str(config["push_branch"]),
    ]
    if config.get("require_clean"):
        command.append("--require-clean")
    if args.no_push:
        command.append("--no-push")
    if args.no_deploy:
        command.append("--no-deploy")
    if config.get("deploy_mode"):
        command.extend(["--deploy-mode", str(config["deploy_mode"])])
    if config.get("deploy_host"):
        command.extend(["--deploy-host", str(config["deploy_host"])])
    if config.get("deploy_repo_path"):
        command.extend(["--deploy-repo-path", str(config["deploy_repo_path"])])
    if config.get("deploy_fetch_ref"):
        command.extend(["--deploy-fetch-ref", str(config["deploy_fetch_ref"])])
    if config.get("deploy_pull_ref"):
        command.extend(["--deploy-pull-ref", str(config["deploy_pull_ref"])])
    return subprocess.run(command, check=False).returncode


def run_bundle(argv: list[str], script_name: str) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--repo", choices=("data", "assess", "crm", "id", "nexus"))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--no-deploy", action="store_true")
    parser.add_argument("--binding-origin", default="")
    args = parser.parse_args(argv)

    binding_origin = args.binding_origin or default_binding_origin(script_name)
    validate_binding("publish_bundle_dint", binding_origin)

    if not args.all and not args.repo:
        print("publish_bundle_dint FAILED")
        print(" - This is a manual bulk utility. Use --repo <data|assess|crm|id|nexus> or --all.")
        return 1

    wrapper_map = {
        "data": Path(__file__).with_name("publish_data.py"),
        "assess": Path(__file__).with_name("publish_assess.py"),
        "crm": Path(__file__).with_name("publish_crm.py"),
        "id": Path(__file__).with_name("publish_id.py"),
        "nexus": Path(__file__).with_name("publish_nexus.py"),
    }
    targets = list(wrapper_map) if args.all else [args.repo]
    failures: list[str] = []
    for target in targets:
        command = [sys.executable, str(wrapper_map[target])]
        if args.no_push:
            command.append("--no-push")
        if args.no_deploy:
            command.append("--no-deploy")
        if subprocess.run(command, check=False).returncode != 0:
            failures.append(target)

    if failures:
        print("publish_bundle_dint FAILED")
        for failure in failures:
            print(f" - {failure} wrapper failed")
        return 1

    print("publish_bundle_dint OK")
    for target in targets:
        print(f" - {target} wrapper completed")
    return 0
