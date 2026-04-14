from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from typing import Any

from .config import IntMemoryConfig
from .service import IntMemoryService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex session memory sidecar backed by IntBrain.")
    parser.add_argument("--owner-id", type=int, default=None, help="Override INTMEMORY_OWNER_ID for API operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Sync Codex sessions into IntBrain.")
    sync_parser.add_argument("--incremental", action="store_true", help="Process only new bytes since the last sync.")
    sync_parser.add_argument("--since", type=str, default=None, help="Process sessions updated since ISO timestamp.")
    sync_parser.add_argument("--file", type=str, default=None, help="Process a single session file.")
    sync_parser.add_argument("--dry-run", action="store_true", help="Parse and extract without writing to IntBrain.")

    search_parser = subparsers.add_parser("search", help="Search stored memory items via IntBrain context/retrieve.")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--days", type=int, default=None)
    search_parser.add_argument("--repo", type=str, default=None)

    recent_parser = subparsers.add_parser("recent", help="Summarize recent work from session JSONL files.")
    recent_parser.add_argument("--days", type=int, default=7)
    recent_parser.add_argument("--limit", type=int, default=10)
    recent_parser.add_argument("--repo", type=str, default=None)

    brief_parser = subparsers.add_parser("session-brief", help="Build a short brief for one session.")
    brief_parser.add_argument("--session-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    service = IntMemoryService(IntMemoryConfig.from_env())
    result = dispatch(service, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def dispatch(service: IntMemoryService, args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "sync":
        return service.sync(
            incremental=bool(args.incremental or (not args.file and not args.since)),
            since=args.since,
            file_path=args.file,
            dry_run=bool(args.dry_run),
            owner_id=args.owner_id,
        )
    if args.command == "search":
        return service.search(
            query=args.query,
            limit=args.limit,
            days=args.days,
            repo=args.repo,
            owner_id=args.owner_id,
        )
    if args.command == "recent":
        return service.recent_work(days=args.days, limit=args.limit, repo=args.repo)
    if args.command == "session-brief":
        brief = service.session_brief(session_id=args.session_id)
        return {"found": brief is not None, "brief": asdict(brief) if brief else None}
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
