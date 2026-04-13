#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def resolve_root_path(explicit_root: str | None) -> Path:
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()

    for candidate in (Path("/int"), Path("D:/int")):
        if candidate.exists():
            return candidate.resolve()

    return Path.cwd().resolve()


def discover_repos(root: Path, explicit_repos: list[str]) -> list[Path]:
    if explicit_repos:
        return [Path(item).expanduser().resolve() for item in explicit_repos]

    repos: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if (child / ".git").exists():
            repos.append(child.resolve())
    return repos


def run_git(repo: Path, *args: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
    return completed.returncode, output


def parse_ahead_behind(raw: str) -> tuple[int, int]:
    parts = [part for part in raw.split() if part]
    if len(parts) < 2:
        raise ValueError(f"unexpected ahead/behind output: '{raw}'")
    return int(parts[0]), int(parts[1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two-phase git sync gate for /int top-level repositories")
    parser.add_argument("--stage", choices=("start", "finish"), default="start")
    parser.add_argument("--root-path", default="")
    parser.add_argument("--repos", nargs="*", default=[])
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def render_table(rows: list[dict[str, object]]) -> str:
    headers = ["repo", "stage", "status", "branch", "upstream", "clean", "behind", "ahead"]
    widths = {key: len(key) for key in headers}
    for row in rows:
        for key in headers:
            widths[key] = max(widths[key], len(str(row.get(key, ""))))

    def fmt(row: dict[str, object]) -> str:
        return "  ".join(str(row.get(key, "")).ljust(widths[key]) for key in headers)

    line_header = "  ".join(key.ljust(widths[key]) for key in headers)
    line_sep = "  ".join("-" * widths[key] for key in headers)
    body = [fmt(row) for row in rows]
    return "\n".join([line_header, line_sep, *body])


def main() -> int:
    args = build_parser().parse_args()

    root = resolve_root_path(args.root_path or None)
    repos = discover_repos(root, args.repos)
    if not repos:
        print(f"No git repositories found for gate under '{root}'.", file=sys.stderr)
        return 2

    results: list[dict[str, object]] = []

    for repo in repos:
        entry: dict[str, object] = {
            "repo": str(repo),
            "stage": args.stage,
            "branch": "",
            "upstream": "",
            "clean": False,
            "ahead": 0,
            "behind": 0,
            "status": "pending",
            "actions": [],
            "error": "",
        }

        actions: list[str] = []

        try:
            if not repo.exists():
                raise RuntimeError("repository path does not exist")
            if not (repo / ".git").exists():
                raise RuntimeError("not a git repository")

            code, branch_out = run_git(repo, "branch", "--show-current")
            if code != 0 or not branch_out.strip():
                raise RuntimeError("cannot resolve current branch")
            branch = branch_out.strip()
            entry["branch"] = branch

            code, upstream_out = run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            if code != 0 or not upstream_out.strip():
                raise RuntimeError("upstream is not configured")
            upstream = upstream_out.strip()
            entry["upstream"] = upstream

            code, status_out = run_git(repo, "status", "--porcelain", "--untracked-files=all")
            if code != 0:
                raise RuntimeError(f"git status failed: {status_out}")
            is_clean = not status_out.strip()
            entry["clean"] = is_clean

            code, counts_out = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...{branch}")
            if code != 0:
                raise RuntimeError(f"cannot evaluate ahead/behind: {counts_out}")
            behind, ahead = parse_ahead_behind(counts_out)
            entry["behind"] = behind
            entry["ahead"] = ahead

            if args.stage == "start":
                if not is_clean:
                    raise RuntimeError("working tree is not clean (start gate requires clean tree before pull)")
                if ahead > 0:
                    raise RuntimeError(f"unpushed commits detected (ahead={ahead}); push previous work before new session")

                if args.dry_run:
                    actions.append("dry-run: would run git pull --ff-only")
                else:
                    code, pull_out = run_git(repo, "pull", "--ff-only")
                    if code != 0:
                        raise RuntimeError(f"git pull --ff-only failed: {pull_out}")
                    actions.append("git pull --ff-only")

                    code, post_counts = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...{branch}")
                    if code == 0:
                        behind, ahead = parse_ahead_behind(post_counts)
                        entry["behind"] = behind
                        entry["ahead"] = ahead
                    if entry["behind"] or entry["ahead"]:
                        raise RuntimeError(
                            f"repository is not synchronized after pull (behind={entry['behind']}, ahead={entry['ahead']})"
                        )
            else:
                if not is_clean:
                    raise RuntimeError("working tree is not clean (finish gate requires commit/stage discipline before push)")
                if behind > 0:
                    raise RuntimeError(f"branch is behind upstream (behind={behind}); run start gate/rebase before finish")

                if ahead > 0:
                    if not args.push:
                        raise RuntimeError(f"unpushed commits detected (ahead={ahead}); rerun finish gate with --push")

                    if args.dry_run:
                        actions.append("dry-run: would run git push")
                    else:
                        code, push_out = run_git(repo, "push")
                        if code != 0:
                            raise RuntimeError(f"git push failed: {push_out}")
                        actions.append("git push")

                        code, post_counts = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...{branch}")
                        if code == 0:
                            behind, ahead = parse_ahead_behind(post_counts)
                            entry["behind"] = behind
                            entry["ahead"] = ahead
                        if entry["behind"] or entry["ahead"]:
                            raise RuntimeError(
                                f"repository is not synchronized after push (behind={entry['behind']}, ahead={entry['ahead']})"
                            )
                else:
                    actions.append("no local commits to push")

            entry["status"] = "ok"
            entry["actions"] = actions
        except Exception as exc:  # noqa: BLE001
            entry["status"] = "blocked"
            entry["actions"] = actions
            entry["error"] = str(exc)

        results.append(entry)

    blocked = [item for item in results if item["status"] != "ok"]

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))
    else:
        print(render_table(results))
        for row in results:
            actions = row.get("actions", [])
            error = str(row.get("error", "")).strip()
            if actions:
                print(f"[{row['repo']}] actions: {'; '.join(actions)}")
            if error:
                print(f"[{row['repo']}] error: {error}", file=sys.stderr)

    return 20 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
