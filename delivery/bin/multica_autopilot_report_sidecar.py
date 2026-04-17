#!/usr/bin/env python3
"""Deliver Multica autopilot reports to existing issues and Probe outbox."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


DEFAULT_AUTOPILOT_ID = "6053a2d3-682f-48ca-a76a-ba1f09faa5e5"
DEFAULT_SERVICE_ID = "intdata-stale-issues-monitor"
DEFAULT_MESSAGE_KIND = "autopilot_digest"
ACTIVE_STATUSES = {"todo", "in_progress", "blocked"}
TERMINAL_STATUSES = {"done", "cancelled"}


class SidecarError(Exception):
    """Base sidecar error."""


class ConfigError(SidecarError):
    """Runtime configuration is missing or invalid."""


class DeliveryError(SidecarError):
    """A delivery phase failed."""


@dataclass(frozen=True)
class Target:
    autopilot_id: str
    master_issue_id: str


@dataclass(frozen=True)
class DeliveryConfig:
    service_id: str
    message_kind: str
    state_path: Path
    probe_enqueue_cmd: list[str]
    dry_run: bool
    skip_telegram: bool


class JsonState:
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as exc:
            raise ConfigError(f"state file is not valid JSON: {self.path}: {exc}") from exc

    def delivery(self, dedupe_key: str) -> dict[str, Any]:
        deliveries = self.data.setdefault("deliveries", {})
        if not isinstance(deliveries, dict):
            deliveries = {}
            self.data["deliveries"] = deliveries
        item = deliveries.setdefault(dedupe_key, {})
        if not isinstance(item, dict):
            item = {}
            deliveries[dedupe_key] = item
        return item

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class MulticaCli:
    def __init__(self, binary: str = "multica", extra_args: Iterable[str] = ()):
        self.binary = binary
        self.extra_args = list(extra_args)

    def _run(self, args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.binary, *self.extra_args, *args],
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _json(self, args: list[str], *, input_text: str | None = None) -> Any:
        proc = self._run(args, input_text=input_text)
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip()
            raise DeliveryError(f"multica command failed ({' '.join(args)}): {detail}")
        try:
            return json.loads(proc.stdout or "null")
        except json.JSONDecodeError as exc:
            raise DeliveryError(f"multica command returned invalid JSON ({' '.join(args)}): {exc}") from exc

    def list_issues(self, *, limit: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        offset = 0
        for _ in range(max_pages):
            payload = self._json(["issue", "list", "--output", "json", "--limit", str(limit), "--offset", str(offset)])
            page = payload.get("issues", []) if isinstance(payload, dict) else []
            if not isinstance(page, list):
                raise DeliveryError("multica issue list returned an unexpected payload")
            issues.extend(item for item in page if isinstance(item, dict))
            if not isinstance(payload, dict) or not payload.get("has_more"):
                break
            offset += limit
        return issues

    def issue_runs(self, issue_id: str) -> list[dict[str, Any]]:
        payload = self._json(["issue", "runs", issue_id, "--output", "json"])
        if not isinstance(payload, list):
            raise DeliveryError(f"multica issue runs returned an unexpected payload for {issue_id}")
        return [item for item in payload if isinstance(item, dict)]

    def add_comment(self, issue_id: str, content: str) -> Any:
        return self._json(["issue", "comment", "add", issue_id, "--content-stdin", "--output", "json"], input_text=content)


class ProbeOutboxCli:
    def __init__(self, command: list[str]):
        self.command = command

    def enqueue(self, *, service_id: str, message_kind: str, title: str, body: str, dedupe_key: str) -> None:
        cmd = [
            *self.command,
            "--service-id",
            service_id,
            "--message-kind",
            message_kind,
            "--title",
            title,
            "--dedupe-key",
            dedupe_key,
        ]
        proc = subprocess.run(cmd, input=body, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            raise DeliveryError(f"probe outbox enqueue failed: {proc.stderr.strip() or proc.stdout.strip()}")


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw).astimezone(UTC)
    except ValueError:
        return None


def _hours_old(value: Any, now: datetime) -> float | None:
    parsed = _parse_ts(value)
    if not parsed:
        return None
    return max(0.0, (now - parsed).total_seconds() / 3600)


def _issue_label(issue: dict[str, Any]) -> str:
    return str(issue.get("identifier") or issue.get("number") or issue.get("id") or "<unknown>")


def _run_is_empty(run: dict[str, Any]) -> bool:
    result = run.get("result")
    if not result:
        return True
    if isinstance(result, dict):
        output = str(result.get("output") or "").strip()
        pr_url = str(result.get("pr_url") or "").strip()
        return not output and not pr_url
    return False


def build_hygiene_report(
    *,
    autopilot_id: str,
    issues: list[dict[str, Any]],
    runs_by_issue: dict[str, list[dict[str, Any]]],
    now: datetime | None = None,
    stale_hours: float = 6.0,
    run_window_hours: float = 24.0,
) -> str:
    now = now or datetime.now(UTC)
    active = [i for i in issues if str(i.get("status", "")).strip() in ACTIVE_STATUSES]
    blocked = [i for i in active if str(i.get("status", "")).strip() == "blocked"]
    stale = [
        i
        for i in active
        if str(i.get("status", "")).strip() == "in_progress"
        and (_hours_old(i.get("updated_at"), now) is not None and _hours_old(i.get("updated_at"), now) >= stale_hours)
    ]
    todo_vague = [
        i
        for i in active
        if str(i.get("status", "")).strip() == "todo"
        and not any(marker in str(i.get("description") or "").lower() for marker in ("acceptance", "done", "next", "критер", "шаг"))
    ]

    cutoff = now - timedelta(hours=run_window_hours)
    failed_runs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    empty_runs: list[dict[str, Any]] = []
    for issue in active:
        issue_id = str(issue.get("id") or "")
        runs = runs_by_issue.get(issue_id, [])
        if not runs:
            empty_runs.append(issue)
            continue
        if any(_run_is_empty(run) for run in runs):
            empty_runs.append(issue)
        for run in runs:
            run_time = _parse_ts(run.get("completed_at")) or _parse_ts(run.get("created_at"))
            if run_time and run_time < cutoff:
                continue
            if str(run.get("status", "")).strip() in {"failed", "cancelled"}:
                failed_runs.append((issue, run))

    lines = [
        f"Краткий hygiene-аудит Multica ({now.strftime('%Y-%m-%d %H:%M UTC')}).",
        "",
        f"Autopilot: `{autopilot_id}`",
        "",
        "1. Urgent blockers",
    ]
    if blocked:
        for issue in blocked[:10]:
            lines.append(f"- {_issue_label(issue)} - {issue.get('title', '')} ({issue.get('priority', 'priority?')}): нужен явный unblock-plan или возврат в todo.")
    else:
        lines.append("- Критичных blocked-задач в активной выборке не найдено.")

    lines.extend(["", f"2. Stale in_progress (> {stale_hours:g}ч без апдейта)"])
    if stale:
        for issue in sorted(stale, key=lambda item: _hours_old(item.get("updated_at"), now) or 0, reverse=True)[:15]:
            age = _hours_old(issue.get("updated_at"), now)
            lines.append(f"- {_issue_label(issue)} - ~{age:.1f}ч: {issue.get('title', '')}")
    else:
        lines.append("- Stale in_progress не найдено.")

    lines.extend(["", "3. todo без actionable acceptance"])
    if todo_vague:
        for issue in todo_vague[:15]:
            lines.append(f"- {_issue_label(issue)} - {issue.get('title', '')}")
    else:
        lines.append("- Критичных todo с размытым acceptance не обнаружено.")

    lines.extend(["", f"4. Failed/cancelled/empty runs ({run_window_hours:g}ч)"])
    if failed_runs:
        lines.append("Failed/cancelled runs:")
        for issue, run in failed_runs[:15]:
            lines.append(f"- {_issue_label(issue)}: run {run.get('id', '<unknown>')} ({run.get('status', 'unknown')})")
    else:
        lines.append("- Failed/cancelled runs в активной выборке не найдены.")
    if empty_runs:
        labels = ", ".join(_issue_label(issue) for issue in empty_runs[:15])
        lines.append(f"- Empty/no runs: {labels}.")

    lines.extend(["", "5. Safe next steps"])
    if blocked:
        lines.append("- По blocked: зафиксировать unblock-plan или снять blocked.")
    if stale:
        lines.append("- По stale in_progress: короткий owner-check, ближайший проверяемый шаг или pause/todo.")
    if failed_runs:
        lines.append("- По failed/cancelled runs: добавить краткий postmortem-комментарий.")
    if not (blocked or stale or failed_runs):
        lines.append("- Дополнительных owner actions по активной выборке не требуется.")

    lines.extend(["", "6. Что стоит re-assign или pause"])
    candidates = sorted(stale, key=lambda item: _hours_old(item.get("updated_at"), now) or 0, reverse=True)[:5]
    if candidates:
        lines.append("- Owner-check / re-assign priority: " + ", ".join(_issue_label(issue) for issue in candidates) + ".")
    else:
        lines.append("- Явных кандидатов на re-assign/pause по stale-сигналу нет.")

    return "\n".join(lines).strip() + "\n"


def parse_targets(raw_values: list[str], env_value: str) -> dict[str, str]:
    targets: dict[str, str] = {}
    if env_value.strip():
        try:
            payload = json.loads(env_value)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"AUTOPILOT_REPORT_TARGETS must be JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ConfigError("AUTOPILOT_REPORT_TARGETS must be a JSON object")
        for autopilot_id, value in payload.items():
            if isinstance(value, str):
                master_issue_id = value
            elif isinstance(value, dict):
                master_issue_id = str(value.get("master_issue_id") or value.get("issue_id") or "")
            else:
                master_issue_id = ""
            if str(autopilot_id).strip() and master_issue_id.strip():
                targets[str(autopilot_id).strip()] = master_issue_id.strip()
    for raw in raw_values:
        if "=" not in raw:
            raise ConfigError(f"--target must be autopilot_id=master_issue_id, got: {raw}")
        autopilot_id, issue_id = raw.split("=", 1)
        if not autopilot_id.strip() or not issue_id.strip():
            raise ConfigError(f"--target must be autopilot_id=master_issue_id, got: {raw}")
        targets[autopilot_id.strip()] = issue_id.strip()
    return targets


def default_state_path() -> Path:
    configured = os.environ.get("AUTOPILOT_REPORT_STATE_PATH", "").strip()
    if configured:
        return Path(configured)
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return root / "inttools" / "autopilot-report-sidecar" / "state.json"


def default_probe_enqueue_cmd() -> list[str]:
    configured = os.environ.get("PROBE_OUTBOX_ENQUEUE_CMD", "").strip()
    if configured:
        return configured.split()
    candidates = [
        Path("/int/probe/probes/probe_outbox_enqueue.py"),
        Path("D:/int/probe/probes/probe_outbox_enqueue.py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return [sys.executable, str(candidate)]
    return [sys.executable, "/int/probe/probes/probe_outbox_enqueue.py"]


def collect_runs(multica: MulticaCli, issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        if str(issue.get("status", "")) in TERMINAL_STATUSES:
            continue
        issue_id = str(issue.get("id") or "")
        if not issue_id:
            continue
        try:
            result[issue_id] = multica.issue_runs(issue_id)
        except DeliveryError:
            result[issue_id] = []
    return result


def deliver_report(
    *,
    target: Target,
    dedupe_key: str,
    report: str,
    config: DeliveryConfig,
    state: JsonState,
    multica: MulticaCli,
    outbox: ProbeOutboxCli,
) -> dict[str, Any]:
    item = state.delivery(dedupe_key)
    result: dict[str, Any] = {
        "dedupe_key": dedupe_key,
        "comment_posted": bool(item.get("comment_posted")),
        "telegram_enqueued": bool(item.get("telegram_enqueued")),
    }
    title = f"Multica autopilot digest: {target.autopilot_id}"

    if config.dry_run:
        result.update({"dry_run": True, "master_issue_id": target.master_issue_id, "report": report})
        return result

    if not item.get("comment_posted"):
        multica.add_comment(target.master_issue_id, report)
        item["comment_posted"] = True
        item["comment_posted_at"] = datetime.now(UTC).isoformat()
        item["master_issue_id"] = target.master_issue_id
        state.save()
        result["comment_posted"] = True

    if not config.skip_telegram and not item.get("telegram_enqueued"):
        try:
            outbox.enqueue(
                service_id=config.service_id,
                message_kind=config.message_kind,
                title=title,
                body=report,
                dedupe_key=dedupe_key,
            )
        except DeliveryError as exc:
            item["telegram_error"] = str(exc)
            item["telegram_failed_at"] = datetime.now(UTC).isoformat()
            state.save()
            raise
        item["telegram_enqueued"] = True
        item["telegram_enqueued_at"] = datetime.now(UTC).isoformat()
        state.save()
        result["telegram_enqueued"] = True

    return result


def run_once(
    *,
    target: Target,
    period_key: str,
    config: DeliveryConfig,
    multica: MulticaCli,
    outbox: ProbeOutboxCli,
    state: JsonState,
    dedupe_key: str | None = None,
    stale_hours: float = 6.0,
    run_window_hours: float = 24.0,
) -> dict[str, Any]:
    resolved_dedupe = dedupe_key or f"multica-autopilot:{target.autopilot_id}:{period_key}"
    delivery_state = state.delivery(resolved_dedupe)
    if delivery_state.get("comment_posted") and (config.skip_telegram or delivery_state.get("telegram_enqueued")):
        return {"dedupe_key": resolved_dedupe, "skipped": True, "reason": "already_delivered"}
    issues = multica.list_issues()
    runs_by_issue = collect_runs(multica, issues)
    report = build_hygiene_report(
        autopilot_id=target.autopilot_id,
        issues=issues,
        runs_by_issue=runs_by_issue,
        stale_hours=stale_hours,
        run_window_hours=run_window_hours,
    )
    return deliver_report(target=target, dedupe_key=resolved_dedupe, report=report, config=config, state=state, multica=multica, outbox=outbox)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deliver Multica autopilot reports to existing issue comments and Probe outbox.")
    parser.add_argument("--autopilot-id", action="append", default=[], help="Autopilot id to deliver. Defaults to the hygiene autopilot id.")
    parser.add_argument("--target", action="append", default=[], help="Mapping autopilot_id=master_issue_id. Merged with AUTOPILOT_REPORT_TARGETS.")
    parser.add_argument("--period-key", default=datetime.now(UTC).strftime("%Y-%m-%d"), help="Period key for dedupe. Default: current UTC date.")
    parser.add_argument("--dedupe-key", default="", help="Explicit dedupe key for a single autopilot run.")
    parser.add_argument("--state-path", default=str(default_state_path()), help="External runtime state path.")
    parser.add_argument("--multica-bin", default=os.environ.get("MULTICA_BIN", "multica"), help="Multica CLI binary.")
    parser.add_argument("--dry-run", action="store_true", help="Render report and target resolution without side effects.")
    parser.add_argument("--skip-telegram", action="store_true", help="Post/comment only; do not enqueue Probe outbox.")
    parser.add_argument("--stale-hours", type=float, default=float(os.environ.get("AUTOPILOT_REPORT_STALE_HOURS", "6")), help="Stale in_progress threshold.")
    parser.add_argument("--run-window-hours", type=float, default=float(os.environ.get("AUTOPILOT_REPORT_RUN_WINDOW_HOURS", "24")), help="Run history window.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        targets = parse_targets(args.target, os.environ.get("AUTOPILOT_REPORT_TARGETS", ""))
        autopilot_ids = args.autopilot_id or [DEFAULT_AUTOPILOT_ID]
        missing = [item for item in autopilot_ids if item not in targets]
        if missing:
            raise ConfigError("missing AUTOPILOT_REPORT_TARGETS mapping for: " + ", ".join(missing))
        if args.dedupe_key and len(autopilot_ids) != 1:
            raise ConfigError("--dedupe-key can be used only with one --autopilot-id")

        config = DeliveryConfig(
            service_id=os.environ.get("AUTOPILOT_REPORT_TELEGRAM_SERVICE_ID", DEFAULT_SERVICE_ID).strip() or DEFAULT_SERVICE_ID,
            message_kind=os.environ.get("AUTOPILOT_REPORT_MESSAGE_KIND", DEFAULT_MESSAGE_KIND).strip() or DEFAULT_MESSAGE_KIND,
            state_path=Path(args.state_path),
            probe_enqueue_cmd=default_probe_enqueue_cmd(),
            dry_run=bool(args.dry_run),
            skip_telegram=bool(args.skip_telegram),
        )
        state = JsonState(config.state_path)
        multica = MulticaCli(args.multica_bin)
        outbox = ProbeOutboxCli(config.probe_enqueue_cmd)
        results = []
        for autopilot_id in autopilot_ids:
            target = Target(autopilot_id=autopilot_id, master_issue_id=targets[autopilot_id])
            results.append(
                run_once(
                    target=target,
                    period_key=args.period_key,
                    config=config,
                    multica=multica,
                    outbox=outbox,
                    state=state,
                    dedupe_key=args.dedupe_key or None,
                    stale_hours=args.stale_hours,
                    run_window_hours=args.run_window_hours,
                )
            )
        print(json.dumps({"ok": True, "results": results}, ensure_ascii=False, indent=2))
        return 0
    except ConfigError as exc:
        print(json.dumps({"ok": False, "error": "config_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except DeliveryError as exc:
        print(json.dumps({"ok": False, "error": "delivery_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
