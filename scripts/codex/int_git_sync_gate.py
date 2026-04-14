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


def resolve_current_repo() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError("current working directory is not inside a git repository")
    return Path(completed.stdout.strip()).resolve()


def discover_repos(root: Path, explicit_repos: list[str], all_repos: bool) -> list[Path]:
    if explicit_repos:
        return [Path(item).expanduser().resolve() for item in explicit_repos]

    if all_repos:
        repos: list[Path] = []
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if (child / ".git").exists():
                repos.append(child.resolve())
        return repos

    return [resolve_current_repo()]


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


def parse_upstream(upstream: str) -> tuple[str, str]:
    parts = upstream.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"unexpected upstream format: '{upstream}'")
    return parts[0], parts[1]


def get_git_dir(repo: Path) -> Path:
    code, git_dir = run_git(repo, "rev-parse", "--git-dir")
    if code != 0 or not git_dir.strip():
        raise RuntimeError(f"cannot resolve git dir: {git_dir}")
    git_path = Path(git_dir.strip())
    return git_path if git_path.is_absolute() else (repo / git_path).resolve()


def ensure_no_in_progress_ops(repo: Path) -> None:
    git_dir = get_git_dir(repo)
    for marker in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "rebase-apply", "rebase-merge"):
        if (git_dir / marker).exists():
            raise RuntimeError(f"merge/rebase operation in progress ({marker})")


def refresh_ahead_behind(repo: Path, upstream: str) -> tuple[int, int]:
    code, counts_out = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
    if code != 0:
        raise RuntimeError(f"cannot evaluate ahead/behind: {counts_out}")
    return parse_ahead_behind(counts_out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two-phase git sync gate for /int repositories")
    parser.add_argument("--stage", choices=("start", "finish"), default="start")
    parser.add_argument("--root-path", default="")
    parser.add_argument("--repos", nargs="*", default=[])
    parser.add_argument("--all-repos", action="store_true")
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

    if args.root_path and not args.all_repos and not args.repos:
        print("--root-path is only supported together with --all-repos or explicit --repos.", file=sys.stderr)
        return 2

    root = resolve_root_path(args.root_path or None)
    repos = discover_repos(root, args.repos, args.all_repos)
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
            "upstream_remote": "",
            "upstream_branch": "",
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
            upstream_remote, upstream_branch = parse_upstream(upstream)
            entry["upstream"] = upstream
            entry["upstream_remote"] = upstream_remote
            entry["upstream_branch"] = upstream_branch

            code, status_out = run_git(repo, "status", "--porcelain", "--untracked-files=all")
            if code != 0:
                raise RuntimeError(f"git status failed: {status_out}")
            is_clean = not status_out.strip()
            entry["clean"] = is_clean

            if not is_clean:
                if args.stage == "start":
                    raise RuntimeError("working tree is not clean (start gate requires clean tree before fetch/pull)")
                raise RuntimeError("working tree is not clean (finish gate requires commit/stage discipline before push)")

            ensure_no_in_progress_ops(repo)

            if args.dry_run:
                actions.append(f"dry-run: would run git fetch --prune {upstream_remote}")
            else:
                code, fetch_out = run_git(repo, "fetch", "--prune", upstream_remote)
                if code != 0:
                    raise RuntimeError(f"git fetch --prune {upstream_remote} failed: {fetch_out}")
                actions.append(f"git fetch --prune {upstream_remote}")

            behind, ahead = refresh_ahead_behind(repo, upstream)
            entry["behind"] = behind
            entry["ahead"] = ahead

            if args.stage == "start":
                if ahead > 0:
                    raise RuntimeError(f"unpushed commits detected (ahead={ahead}); push previous work before new session")

                if behind > 0:
                    if args.dry_run:
                        actions.append(f"dry-run: would run git pull --ff-only {upstream_remote} {upstream_branch}")
                    else:
                        code, pull_out = run_git(repo, "pull", "--ff-only", upstream_remote, upstream_branch)
                        if code != 0:
                            raise RuntimeError(f"git pull --ff-only {upstream_remote} {upstream_branch} failed: {pull_out}")
                        actions.append(f"git pull --ff-only {upstream_remote} {upstream_branch}")
                        behind, ahead = refresh_ahead_behind(repo, upstream)
                        entry["behind"] = behind
                        entry["ahead"] = ahead

                if not args.dry_run and (behind > 0 or ahead > 0):
                    raise RuntimeError(
                        f"repository is not synchronized after start gate (behind={entry['behind']}, ahead={entry['ahead']})"
                    )
                if behind == 0 and ahead == 0:
                    actions.append("repository already synchronized")
            else:
                if behind > 0:
                    raise RuntimeError(f"branch is behind upstream (behind={behind}); resolve remote changes before finish")

                if ahead > 0:
                    if not args.push:
                        raise RuntimeError(f"unpushed commits detected (ahead={ahead}); rerun finish gate with --push")
                    if args.dry_run:
                        actions.append(f"dry-run: would run git push {upstream_remote} {branch}:{upstream_branch}")
                    else:
                        code, push_out = run_git(repo, "push", upstream_remote, f"{branch}:{upstream_branch}")
                        if code != 0:
                            raise RuntimeError(f"git push {upstream_remote} {branch}:{upstream_branch} failed: {push_out}")
                        actions.append(f"git push {upstream_remote} {branch}:{upstream_branch}")

                        code, fetch_out = run_git(repo, "fetch", "--prune", upstream_remote)
                        if code != 0:
                            raise RuntimeError(f"post-push git fetch --prune {upstream_remote} failed: {fetch_out}")
                        actions.append(f"git fetch --prune {upstream_remote} (post-push)")

                        behind, ahead = refresh_ahead_behind(repo, upstream)
                        entry["behind"] = behind
                        entry["ahead"] = ahead
                        if behind > 0 or ahead > 0:
                            raise RuntimeError(
                                f"repository is not synchronized after push verification (behind={entry['behind']}, ahead={entry['ahead']})"
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
