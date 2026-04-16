#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Moscow")
DEFAULT_WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", "/2brain/Resources/OpenClaw")).resolve()
DEFAULT_REGISTRY = DEFAULT_WORKSPACE / "Jobs-Registry.md"


def resolve_openclaw_bin() -> str:
    env_path = os.environ.get("OPENCLAW_BIN")
    if env_path:
        return env_path
    found = shutil.which("openclaw")
    if found:
        return found
    fallback = Path.home() / ".local/bin/openclaw"
    return str(fallback)


OPENCLAW = resolve_openclaw_bin()
REGISTRY = Path(os.environ.get("OPENCLAW_JOBS_REGISTRY", str(DEFAULT_REGISTRY))).resolve()


def now_msk() -> datetime:
    return datetime.now(TZ)


def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def run_openclaw_cron_list() -> dict:
    proc = subprocess.run(
        [OPENCLAW, "cron", "list", "--all", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def normalize_job(job: dict) -> dict:
    delivery = job.get("delivery") or {}
    payload = job.get("payload") or {}
    schedule = job.get("schedule") or {}
    return {
        "id": job.get("id"),
        "name": job.get("name") or "",
        "enabled": bool(job.get("enabled")),
        "schedule": schedule,
        "sessionTarget": job.get("sessionTarget"),
        "delivery": {
            "mode": delivery.get("mode"),
            "to": delivery.get("to"),
        },
        "payload": {
            "kind": payload.get("kind"),
        },
    }


def render_job_block(job: dict) -> str:
    schedule = json.dumps(job["schedule"], ensure_ascii=False, sort_keys=True)
    delivery = json.dumps(job["delivery"], ensure_ascii=False, sort_keys=True)
    payload = json.dumps(job["payload"], ensure_ascii=False, sort_keys=True)
    status = "enabled" if job["enabled"] else "disabled"
    name = job["name"] or "(без имени)"
    return (
        f"### {job['id']} — {name}\n"
        f"- status: {status}\n"
        f"- sessionTarget: {job['sessionTarget']}\n"
        f"- schedule: `{schedule}`\n"
        f"- delivery: `{delivery}`\n"
        f"- payload: `{payload}`\n"
    )


def parse_existing_snapshot(text: str) -> list[dict] | None:
    start = "<!-- SNAPSHOT:BEGIN -->"
    end = "<!-- SNAPSHOT:END -->"
    if start not in text or end not in text:
        return None
    chunk = text.split(start, 1)[1].split(end, 1)[0].strip()
    if not chunk:
        return None
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        return None


def load_history(text: str) -> str:
    marker = "## История изменений\n"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def diff_lines(old: list[dict], new: list[dict]) -> list[str]:
    old_map = {j["id"]: j for j in old}
    new_map = {j["id"]: j for j in new}
    lines: list[str] = []
    for job_id in sorted(new_map.keys() - old_map.keys()):
        lines.append(f"- Added {job_id} — {new_map[job_id].get('name') or '(без имени)'}")
    for job_id in sorted(old_map.keys() - new_map.keys()):
        lines.append(f"- Removed {job_id} — {old_map[job_id].get('name') or '(без имени)'}")
    for job_id in sorted(new_map.keys() & old_map.keys()):
        if old_map[job_id] != new_map[job_id]:
            lines.append(f"- Changed {job_id} — {new_map[job_id].get('name') or '(без имени)'}")
    return lines


def build_document(snapshot: list[dict], previous_text: str, change_lines: list[str]) -> str:
    ts = fmt_ts(now_msk())
    total = len(snapshot)
    enabled = sum(1 for j in snapshot if j["enabled"])
    disabled = total - enabled
    jobs_block = "\n".join(render_job_block(job) for job in snapshot)
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)

    history_prev = load_history(previous_text)
    history_parts = []
    if change_lines:
        history_parts.append(f"### {ts}\n" + "\n".join(change_lines))
    if history_prev:
        history_parts.append(history_prev)
    history = "\n\n".join(history_parts).strip()

    doc = f"""# OpenClaw Jobs Registry

Последнее обновление: {ts}

## Сводка
- Всего jobs: {total}
- Активных: {enabled}
- Отключенных: {disabled}

## Список jobs

{jobs_block}
<!-- SNAPSHOT:BEGIN -->
{snapshot_json}
<!-- SNAPSHOT:END -->

## История изменений
{history}
"""
    return doc.rstrip() + "\n"


def main() -> int:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    data = run_openclaw_cron_list()
    jobs = data.get("jobs") or []
    snapshot = sorted((normalize_job(job) for job in jobs), key=lambda j: (j["name"], j["id"]))

    previous_text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else ""
    previous_snapshot = parse_existing_snapshot(previous_text) or []
    changes = diff_lines(previous_snapshot, snapshot)

    if REGISTRY.exists() and previous_snapshot == snapshot:
        print("NO_CHANGES")
        return 0

    document = build_document(snapshot, previous_text, changes or ["- Initial snapshot"])
    REGISTRY.write_text(document, encoding="utf-8")
    print("UPDATED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"ERROR: missing dependency: {exc}", file=sys.stderr)
        raise
