#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = ROOT_DIR / "codex" / "config" / "agent-tool-routing.v1.json"
SUPPORTED_PLATFORMS = ("windows", "linux", "macos")


class RoutingError(RuntimeError):
    def __init__(self, code: str, message: str, *, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


@dataclass(frozen=True)
class Binding:
    binding_origin: str
    binding_kind: str
    binding_role: str
    binding_origin_type: str
    platforms_supported: tuple[str, ...]
    adapter_targets_engine: str | None
    parity_required: bool


@dataclass(frozen=True)
class Capability:
    capability_id: str
    logical_intents: tuple[str, ...]
    canonical_engine: str
    resolution_status: str
    approved_fallback_skills: tuple[str, ...]
    runtime_bindings: tuple[Binding, ...]


def resolve_registry_path(explicit: str | None = None) -> Path:
    raw = explicit or os.getenv("INT_AGENT_TOOL_ROUTING_REGISTRY", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_REGISTRY_PATH.resolve()


def normalize_platform(raw: str | None = None) -> str:
    if raw:
        value = raw.strip().lower()
    elif sys.platform.startswith("win"):
        value = "windows"
    elif sys.platform == "darwin":
        value = "macos"
    else:
        value = "linux"

    if value not in SUPPORTED_PLATFORMS:
        raise RoutingError("UNSUPPORTED_PLATFORM", f"unsupported platform '{value}'")
    return value


def load_registry(explicit_path: str | None = None) -> dict[str, Any]:
    registry_path = resolve_registry_path(explicit_path)
    if not registry_path.exists():
        raise RoutingError("MISSING_REGISTRY", f"routing registry not found: {registry_path}")
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RoutingError("INVALID_REGISTRY", f"routing registry is not valid JSON: {registry_path}") from exc
    if payload.get("version") != "1":
        raise RoutingError("UNSUPPORTED_REGISTRY_VERSION", f"unsupported routing registry version: {payload.get('version')!r}")
    if not isinstance(payload.get("capabilities"), list):
        raise RoutingError("INVALID_REGISTRY", "routing registry must contain a capabilities array")
    payload["_registry_path"] = str(registry_path)
    return payload


def binding_from_dict(raw: dict[str, Any]) -> Binding:
    return Binding(
        binding_origin=str(raw["binding_origin"]),
        binding_kind=str(raw["binding_kind"]),
        binding_role=str(raw.get("binding_role", "compatibility")),
        binding_origin_type=str(raw.get("binding_origin_type", "repo-path")),
        platforms_supported=tuple(str(item) for item in raw["platforms_supported"]),
        adapter_targets_engine=(str(raw["adapter_targets_engine"]) if raw.get("adapter_targets_engine") else None),
        parity_required=bool(raw.get("parity_required", False)),
    )


def capability_from_dict(raw: dict[str, Any]) -> Capability:
    return Capability(
        capability_id=str(raw["capability_id"]),
        logical_intents=tuple(str(item) for item in raw.get("logical_intents", [])),
        canonical_engine=str(raw["canonical_engine"]),
        resolution_status=str(raw.get("resolution_status", "managed")),
        approved_fallback_skills=tuple(str(item) for item in raw.get("approved_fallback_skills", [])),
        runtime_bindings=tuple(binding_from_dict(item) for item in raw.get("runtime_bindings", [])),
    )


def resolve_path(origin: str, *, registry_path: str | None = None) -> Path:
    # Runtime binding paths are repo-owned paths under the tooling root.
    # Temporary registry copies used by tests must still resolve against the repo.
    base = ROOT_DIR
    return (base / origin).resolve()


def find_capability(payload: dict[str, Any], capability_id: str) -> Capability:
    matches = [capability_from_dict(item) for item in payload["capabilities"] if item.get("capability_id") == capability_id]
    if not matches:
        raise RoutingError("UNKNOWN_CAPABILITY", f"unknown capability '{capability_id}'")
    if len(matches) > 1:
        raise RoutingError("AMBIGUOUS_CAPABILITY", f"capability '{capability_id}' is declared more than once")
    return matches[0]


def find_capability_by_intent(payload: dict[str, Any], intent: str) -> Capability:
    matches = []
    for item in payload["capabilities"]:
        capability = capability_from_dict(item)
        if intent == capability.capability_id or intent in capability.logical_intents:
            matches.append(capability)
    if not matches:
        raise RoutingError("UNKNOWN_INTENT", f"unknown high-risk intent '{intent}'")
    if len(matches) > 1:
        raise RoutingError("AMBIGUOUS_INTENT", f"high-risk intent '{intent}' resolves to multiple capabilities")
    return matches[0]


def validate_capability(capability: Capability, *, registry_path: str | None = None) -> list[str]:
    errors: list[str] = []
    if not capability.logical_intents:
        errors.append(f"{capability.capability_id}: logical_intents must not be empty")
    if not capability.runtime_bindings:
        errors.append(f"{capability.capability_id}: runtime_bindings must not be empty")

    engine_path = resolve_path(capability.canonical_engine, registry_path=registry_path)
    if not engine_path.exists():
        errors.append(f"{capability.capability_id}: missing engine {capability.canonical_engine}")

    engine_bindings = [binding for binding in capability.runtime_bindings if binding.binding_origin == capability.canonical_engine]
    if len(engine_bindings) != 1:
        errors.append(f"{capability.capability_id}: canonical engine must appear exactly once in runtime_bindings")
    elif engine_bindings[0].binding_kind != "engine":
        errors.append(f"{capability.capability_id}: canonical engine binding_kind must be 'engine'")

    primary_by_platform: dict[str, list[str]] = {platform: [] for platform in SUPPORTED_PLATFORMS}
    for binding in capability.runtime_bindings:
        if binding.binding_kind not in ("engine", "adapter"):
            errors.append(f"{capability.capability_id}: unsupported binding_kind '{binding.binding_kind}' for {binding.binding_origin}")
        if binding.binding_role not in ("primary", "compatibility", "canonical"):
            errors.append(f"{capability.capability_id}: unsupported binding_role '{binding.binding_role}' for {binding.binding_origin}")
        for platform in binding.platforms_supported:
            if platform not in SUPPORTED_PLATFORMS:
                errors.append(f"{capability.capability_id}: unsupported platform '{platform}' in {binding.binding_origin}")
            elif binding.binding_role == "primary":
                primary_by_platform[platform].append(binding.binding_origin)
        binding_path = resolve_path(binding.binding_origin, registry_path=registry_path)
        if not binding_path.exists():
            label = "engine" if binding.binding_kind == "engine" else "adapter"
            errors.append(f"{capability.capability_id}: missing {label} {binding.binding_origin}")
        if binding.binding_kind == "adapter":
            if binding.adapter_targets_engine != capability.canonical_engine:
                errors.append(
                    f"{capability.capability_id}: adapter drift for {binding.binding_origin} "
                    f"(targets {binding.adapter_targets_engine!r}, expected {capability.canonical_engine!r})"
                )
        elif binding.adapter_targets_engine is not None:
            errors.append(f"{capability.capability_id}: engine binding {binding.binding_origin} must not declare adapter_targets_engine")

    for platform, bindings in primary_by_platform.items():
        if len(bindings) > 1:
            errors.append(
                f"{capability.capability_id}: platform '{platform}' has multiple primary bindings: {', '.join(bindings)}"
            )
    return errors


def validate_registry(explicit_path: str | None = None) -> dict[str, Any]:
    payload = load_registry(explicit_path)
    seen_capabilities: set[str] = set()
    seen_intents: dict[str, str] = {}
    errors: list[str] = []

    for item in payload["capabilities"]:
        capability = capability_from_dict(item)
        if capability.capability_id in seen_capabilities:
            errors.append(f"duplicate capability_id: {capability.capability_id}")
        seen_capabilities.add(capability.capability_id)
        for intent in capability.logical_intents:
            owner = seen_intents.get(intent)
            if owner and owner != capability.capability_id:
                errors.append(f"logical intent '{intent}' is declared by both {owner} and {capability.capability_id}")
            else:
                seen_intents[intent] = capability.capability_id
        errors.extend(validate_capability(capability, registry_path=payload["_registry_path"]))

    return {
        "ok": not errors,
        "resolution_status": "resolved" if not errors else "blocked",
        "registry_path": payload["_registry_path"],
        "capabilities_count": len(payload["capabilities"]),
        "errors": errors,
    }


def resolve_capability(intent: str, *, platform: str | None = None, registry_path: str | None = None) -> dict[str, Any]:
    payload = load_registry(registry_path)
    capability = find_capability_by_intent(payload, intent)
    normalized_platform = normalize_platform(platform)
    if capability.resolution_status != "managed":
        raise RoutingError(
            capability.resolution_status.upper(),
            f"capability '{capability.capability_id}' is {capability.resolution_status}, not an active managed route",
            payload={
                "capability_id": capability.capability_id,
                "approved_fallback_skills": list(capability.approved_fallback_skills),
            },
        )
    capability_errors = validate_capability(capability, registry_path=payload["_registry_path"])
    if capability_errors:
        first_error = capability_errors[0]
        code = "BLOCKED"
        if "missing engine" in first_error:
            code = "MISSING_ENGINE"
        elif "missing adapter" in first_error:
            code = "MISSING_ADAPTER"
        elif "adapter drift" in first_error:
            code = "ADAPTER_DRIFT"
        raise RoutingError(
            code,
            first_error,
            payload={
                "capability_id": capability.capability_id,
                "approved_fallback_skills": list(capability.approved_fallback_skills)
            },
        )

    primary_bindings = [
        binding
        for binding in capability.runtime_bindings
        if binding.binding_role == "primary" and normalized_platform in binding.platforms_supported
    ]
    if not primary_bindings:
        supported_platforms = {item for binding in capability.runtime_bindings for item in binding.platforms_supported}
        if normalized_platform not in supported_platforms:
            raise RoutingError(
                "UNSUPPORTED_PLATFORM",
                f"capability '{capability.capability_id}' does not support platform '{normalized_platform}'",
                payload={
                    "capability_id": capability.capability_id,
                    "approved_fallback_skills": list(capability.approved_fallback_skills)
                },
            )
        raise RoutingError(
            "MISSING_ADAPTER",
            f"capability '{capability.capability_id}' has no primary binding for platform '{normalized_platform}'",
            payload={
                "capability_id": capability.capability_id,
                "approved_fallback_skills": list(capability.approved_fallback_skills)
            },
        )
    if len(primary_bindings) > 1:
        raise RoutingError(
            "AMBIGUOUS_INTENT",
            f"capability '{capability.capability_id}' has multiple primary bindings for platform '{normalized_platform}'",
            payload={
                "capability_id": capability.capability_id,
                "approved_fallback_skills": list(capability.approved_fallback_skills)
            },
        )

    selected = primary_bindings[0]
    return {
        "resolution_status": "resolved",
        "registry_path": payload["_registry_path"],
        "platform": normalized_platform,
        "capability_id": capability.capability_id,
        "logical_intents": list(capability.logical_intents),
        "canonical_engine": capability.canonical_engine,
        "selected_binding": {
            "binding_origin": selected.binding_origin,
            "binding_kind": selected.binding_kind,
            "binding_role": selected.binding_role,
            "platforms_supported": list(selected.platforms_supported),
            "adapter_targets_engine": selected.adapter_targets_engine,
            "parity_required": selected.parity_required,
        },
        "approved_fallback_skills": list(capability.approved_fallback_skills),
    }


def assert_binding(
    capability_id: str,
    binding_origin: str,
    *,
    platform: str | None = None,
    registry_path: str | None = None,
) -> dict[str, Any]:
    payload = load_registry(registry_path)
    capability = find_capability(payload, capability_id)
    normalized_platform = normalize_platform(platform)
    if capability.resolution_status != "managed":
        raise RoutingError(
            capability.resolution_status.upper(),
            f"capability '{capability.capability_id}' is {capability.resolution_status}, not an active managed route",
            payload={"capability_id": capability.capability_id},
        )
    errors = validate_capability(capability, registry_path=payload["_registry_path"])
    if errors:
        raise RoutingError("BLOCKED", errors[0], payload={"capability_id": capability.capability_id})

    binding = next((item for item in capability.runtime_bindings if item.binding_origin == binding_origin), None)
    if binding is None:
        raise RoutingError(
            "MISSING_ADAPTER",
            f"binding '{binding_origin}' is not declared for capability '{capability_id}'",
            payload={"capability_id": capability_id},
        )
    if normalized_platform not in binding.platforms_supported:
        raise RoutingError(
            "UNSUPPORTED_PLATFORM",
            f"binding '{binding_origin}' does not support platform '{normalized_platform}'",
            payload={"capability_id": capability_id},
        )
    if binding.binding_kind == "adapter" and binding.adapter_targets_engine != capability.canonical_engine:
        raise RoutingError(
            "ADAPTER_DRIFT",
            f"binding '{binding_origin}' targets {binding.adapter_targets_engine!r} instead of {capability.canonical_engine!r}",
            payload={"capability_id": capability_id},
        )
    return {
        "resolution_status": "resolved",
        "platform": normalized_platform,
        "capability_id": capability.capability_id,
        "canonical_engine": capability.canonical_engine,
        "binding_origin": binding.binding_origin,
        "binding_kind": binding.binding_kind,
        "binding_role": binding.binding_role,
        "approved_fallback_skills": list(capability.approved_fallback_skills),
    }


def describe_capability(capability_id: str, *, registry_path: str | None = None) -> dict[str, Any]:
    payload = load_registry(registry_path)
    capability = find_capability(payload, capability_id)
    active_route = capability.resolution_status == "managed"
    return {
        "resolution_status": capability.resolution_status,
        "active_route": active_route,
        "registry_path": payload["_registry_path"],
        "capability_id": capability.capability_id,
        "logical_intents": list(capability.logical_intents),
        "canonical_engine": capability.canonical_engine,
        "approved_fallback_skills": list(capability.approved_fallback_skills),
        "runtime_bindings": [
            {
                "binding_origin": binding.binding_origin,
                "binding_kind": binding.binding_kind,
                "binding_role": binding.binding_role,
                "binding_origin_type": binding.binding_origin_type,
                "platforms_supported": list(binding.platforms_supported),
                "adapter_targets_engine": binding.adapter_targets_engine,
                "parity_required": binding.parity_required,
            }
            for binding in capability.runtime_bindings
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Machine-readable routing registry for repo-owned high-risk capabilities")
    parser.add_argument("--registry-path", default="")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser("resolve", help="Resolve a logical high-risk intent to a primary runtime binding")
    resolve_parser.add_argument("--intent", required=True)
    resolve_parser.add_argument("--platform", default="")
    resolve_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="Validate routing registry invariants")
    validate_parser.add_argument("--strict", action="store_true")
    validate_parser.add_argument("--json", action="store_true")

    describe_parser = subparsers.add_parser("describe", help="Describe one capability from the routing registry")
    describe_parser.add_argument("--capability", required=True)
    describe_parser.add_argument("--json", action="store_true")

    return parser


def print_payload(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    args = build_parser().parse_args()
    registry_path = args.registry_path or None
    try:
        if args.command == "resolve":
            payload = resolve_capability(args.intent, platform=args.platform or None, registry_path=registry_path)
            print_payload(payload, as_json=args.json)
            return 0
        if args.command == "validate":
            payload = validate_registry(registry_path)
            print_payload(payload, as_json=args.json)
            return 0 if payload["ok"] or not args.strict else 1
        if args.command == "describe":
            payload = describe_capability(args.capability, registry_path=registry_path)
            print_payload(payload, as_json=args.json)
            return 0
    except RoutingError as exc:
        payload = {
            "resolution_status": "blocked",
            "error_code": exc.code,
            "error": str(exc),
            **exc.payload,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
