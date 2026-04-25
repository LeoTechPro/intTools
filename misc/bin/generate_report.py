#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    data = json.loads(Path("issues.json").read_text(encoding="utf-8"))
    now = datetime(2026, 3, 25, 6, 0, tzinfo=timezone.utc)

    groups = {">72ч": [], ">48ч": [], ">24ч": []}

    for issue in data:
        updated = datetime.strptime(issue["updatedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_hours = (now - updated).total_seconds() / 3600
        if age_hours > 72:
            groups[">72ч"].append((issue, age_hours))
        elif age_hours > 48:
            groups[">48ч"].append((issue, age_hours))
        elif age_hours > 24:
            groups[">24ч"].append((issue, age_hours))

    print(f"Отчёт по проекту /int/data от {now.strftime('%Y-%m-%d %H:%M UTC')}\n")
    for group in [">72ч", ">48ч", ">24ч"]:
        print(f"🔴 Возраст {group}:")
        if not groups[group]:
            print("  Нет задач")
        for issue, age in sorted(groups[group], key=lambda x: x[1]):
            print(f"  - #{issue['number']} {issue['title']} (обновлено {issue['updatedAt']}, {int(age)}ч назад)")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
