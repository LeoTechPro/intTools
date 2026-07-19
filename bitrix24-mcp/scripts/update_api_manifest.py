"""Build a Bitrix24 REST method manifest from the official documentation repo."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


OFFICIAL_REPOSITORY = "https://github.com/bitrix24/b24restdocs"
METHOD_RE = re.compile(r"(?<![\w.])([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)(?![\w.])")
SINGLE_TOKEN_ENDPOINT_RE = re.compile(
    r"/rest/(?:\*\*put_your_user_id_here\*\*/\*\*put_your_webhook_here\*\*/)?"
    r"([A-Za-z][A-Za-z0-9_-]+)(?=[?`\s])"
)
EXPLICIT_SINGLE_TOKEN_METHODS = {
    "api-reference/common/system/methods.md": "methods",
    "api-reference/common/system/scope.md": "scope",
    "api-reference/common/users/profile.md": "profile",
    "api-reference/events/events.md": "events",
    "settings/how-to-call-rest-api/batch.md": "batch",
}
READ_ACTIONS = {
    "current",
    "download",
    "field",
    "fields",
    "get",
    "getaccess",
    "getanswer",
    "getlist",
    "getmany",
    "history",
    "isexists",
    "list",
    "manifest",
    "methods",
    "events",
    "profile",
    "read",
    "search",
    "settings",
    "scope",
    "status",
}
WRITE_ACTIONS = {
    "activate",
    "add",
    "bind",
    "close",
    "create",
    "delete",
    "import",
    "move",
    "open",
    "pause",
    "recall",
    "register",
    "remove",
    "resume",
    "send",
    "set",
    "start",
    "stop",
    "unbind",
    "unregister",
    "unset",
    "update",
    "upload",
    "vote",
}


def _git_sha(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _first_heading(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("# "):
                return line.strip()
    return ""


def _method_from_heading(heading: str) -> str | None:
    candidates = METHOD_RE.findall(heading)
    if not candidates:
        return None
    candidate = candidates[-1].rstrip(".,;:)")
    if candidate.lower().endswith((".html", ".json", ".md")):
        return None
    return candidate


def _entry_kind(method: str, source_path: str) -> str:
    lowered = method.lower()
    parts = tuple(part.lower() for part in Path(source_path).parts)
    if "outdated" in parts:
        return "outdated"
    if lowered.startswith("bx24."):
        return "browser_js"
    method_parts = lowered.split(".")
    filename = Path(source_path).stem.lower()
    if (
        ".on." in lowered
        or filename.startswith("on-")
        or ("events" in parts and method_parts[0].startswith("on"))
    ):
        return "event"
    return "server_method"


def _risk(method: str, kind: str) -> str:
    if kind != "server_method":
        return "not_callable"
    action = method.lower().split(".")[-1]
    compact_action = re.sub(r"[^a-z]", "", action)
    if action in READ_ACTIONS or compact_action in READ_ACTIONS:
        return "read"
    if action in WRITE_ACTIONS or compact_action in WRITE_ACTIONS:
        return "write"
    if any(compact_action.startswith(prefix) for prefix in ("get", "list", "search", "is", "can", "count")):
        return "read"
    if any(
        compact_action.startswith(prefix)
        for prefix in ("add", "create", "update", "delete", "set", "send", "bind", "move", "start", "stop")
    ):
        return "write"
    return "unknown"


def _method_id(method: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", method.lower()).strip("_")


def _validate_single_token_endpoints(docs_repo: Path) -> list[str]:
    discovered: set[str] = set()
    for source in docs_repo.rglob("*.md"):
        text = source.read_text(encoding="utf-8")
        discovered.update(SINGLE_TOKEN_ENDPOINT_RE.findall(text))
    discovered.discard("method-name")
    unexplained = sorted(discovered - set(EXPLICIT_SINGLE_TOKEN_METHODS.values()))
    if unexplained:
        raise SystemExit(f"unclassified single-token REST endpoints: {unexplained}")
    return sorted(discovered)


def build_manifest(docs_repo: Path) -> dict[str, Any]:
    api_root = docs_repo / "api-reference"
    if not api_root.is_dir():
        raise SystemExit(f"missing api-reference directory: {api_root}")
    single_token_endpoints = _validate_single_token_endpoints(docs_repo)

    grouped: dict[str, dict[str, Any]] = {}
    discovered_pages = 0
    sources = set(api_root.rglob("*.md"))
    for relative_path in EXPLICIT_SINGLE_TOKEN_METHODS:
        source = docs_repo / relative_path
        if not source.is_file():
            raise SystemExit(f"missing documented single-token method page: {source}")
        sources.add(source)

    for source in sorted(sources):
        heading = _first_heading(source)
        source_path = source.relative_to(docs_repo).as_posix()
        method = EXPLICIT_SINGLE_TOKEN_METHODS.get(source_path) or _method_from_heading(heading)
        if method is None:
            continue
        discovered_pages += 1
        key = method.lower()
        kind = _entry_kind(method, source_path)
        entry = grouped.setdefault(
            key,
            {
                "id": _method_id(method),
                "method": method,
                "kind": kind,
                "risk": _risk(method, kind),
                "sources": [],
            },
        )
        entry["sources"].append(source_path)
        if entry["kind"] != kind:
            # Prefer an active callable classification when the same method has
            # both current and historical documentation pages.
            precedence = {"server_method": 4, "event": 3, "browser_js": 2, "outdated": 1}
            if precedence[kind] > precedence[entry["kind"]]:
                entry["kind"] = kind
                entry["risk"] = _risk(method, kind)

    entries = sorted(grouped.values(), key=lambda row: (row["kind"], row["method"].lower()))
    if not entries:
        raise SystemExit("no Bitrix24 method-like documentation pages discovered")

    id_counts = Counter(entry["id"] for entry in entries)
    duplicate_ids = sorted(identifier for identifier, count in id_counts.items() if count > 1)
    if duplicate_ids:
        raise SystemExit(f"manifest id collisions: {duplicate_ids[:10]}")

    kinds = Counter(entry["kind"] for entry in entries)
    risks = Counter(entry["risk"] for entry in entries if entry["kind"] == "server_method")
    return {
        "schema_version": 1,
        "official_repository": OFFICIAL_REPOSITORY,
        "official_commit": _git_sha(docs_repo),
        "discovered_method_pages": discovered_pages,
        "single_token_endpoints": single_token_endpoints,
        "counts": {
            "total_entries": len(entries),
            "server_methods": kinds["server_method"],
            "events": kinds["event"],
            "browser_js": kinds["browser_js"],
            "outdated": kinds["outdated"],
            "read_methods": risks["read"],
            "write_methods": risks["write"],
            "unknown_risk_methods": risks["unknown"],
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-root", type=Path, required=True, help="Checkout of bitrix24/b24restdocs")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "bitrix24_mcp" / "api_manifest.json",
    )
    args = parser.parse_args()
    manifest = build_manifest(args.docs_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {manifest['counts']['server_methods']} active server methods "
        f"from {manifest['official_commit']} to {args.output}"
    )


if __name__ == "__main__":
    main()
