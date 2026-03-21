#!/usr/bin/env python3
"""Simple PARA invariant linter.

Checks nexus PARA rules in the database and exits with code 1 if violations are found.
"""
import os
import sys
import sqlalchemy as sa

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres",
)

CHECKS = {
    "projects_without_area": "SELECT id, name, created_at FROM projects WHERE area_id IS NULL",
    "tasks_without_links": "SELECT id, title, created_at FROM tasks WHERE project_id IS NULL AND area_id IS NULL",
    "resources_without_links": "SELECT id, title, created_at FROM resources WHERE project_id IS NULL AND area_id IS NULL",
    "tasks_area_mismatch": (
        "SELECT t.id, t.title, t.area_id, p.area_id AS project_area_id "
        "FROM tasks t JOIN projects p ON t.project_id = p.id "
        "WHERE t.project_id IS NOT NULL AND t.area_id <> p.area_id"
    ),
    "calendar_items_without_links": "SELECT id, title, start_at FROM calendar_items WHERE project_id IS NULL AND area_id IS NULL",
    "time_entries_without_links": "SELECT id, start_time FROM time_entries WHERE project_id IS NULL AND area_id IS NULL AND task_id IS NULL",
}

def run() -> int:
    try:
        engine = sa.create_engine(DSN)
    except Exception as e:  # pragma: no cover - connection issues
        print(f"Cannot create engine: {e}")
        return 2
    violations = 0
    try:
        with engine.connect() as conn:
            for label, query in CHECKS.items():
                count = conn.execute(sa.text(f"SELECT COUNT(*) FROM ({query}) AS sub")).scalar()
                rows = conn.execute(sa.text(query + " LIMIT 10")).fetchall()
                if count:
                    print(f"{label}: {count}")
                    for row in rows:
                        print("  ", tuple(row))
                    violations += int(count)
                else:
                    print(f"{label}: OK")
    except Exception as e:  # pragma: no cover
        print(f"DB check failed: {e}")
        return 2
    if violations:
        print(f"Total violations: {violations}")
        return 1
    print("All checks passed")
    return 0

if __name__ == "__main__":
    sys.exit(run())
