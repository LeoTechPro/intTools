---
name: review-sql-find
description: 'Read-only PostgreSQL security and performance audit workflow with deterministic section validation and report synthesis. Use when you need to audit a PostgreSQL server from live SQL data or from provided section summaries, detect incomplete or truncated sections, and produce three outputs: Server Security Report, Server Performance Report, and Executive Summary with prioritized recommendations.'
---

# Review SQL Find

## Overview

Run a deterministic, read-only PostgreSQL audit and block final synthesis when any section is incomplete.

## Workflow

1. Select runtime scope before data collection.
- Allowed scope values: `int/data`, `int/assess`, `custom`.
- If scope is not provided, ask once and continue only after scope is explicit.

2. Lock audit mode.
- Default and required mode: `audit_mode=read_only`.
- Never execute mutating SQL (`ALTER`, `CREATE`, `DROP`, `REVOKE`, `GRANT`, `VACUUM FULL`, `REINDEX`, etc.).
- Return SQL only as recommendations.

3. Pick source strategy.
- Prefer `source=live_sql` when MCP Postgres is available.
- Use `source=section_summaries` as fallback when live access is unavailable.

4. Collect and normalize required sections.
- Required section ids:
  - `access_control_roles`
  - `network_security`
  - `auth_ssl`
  - `audit_logging`
  - `connection_management`
  - `query_performance`
  - `wal_checkpoint`
  - `autovacuum`
  - `planner_settings`
  - `parallelism_workers`
  - `extensions`
  - `cache_efficiency`
  - `replication_status`

5. Validate completeness before synthesis.
- Mark section as `INCOMPLETE` if data is truncated, malformed, or missing.
- Do not generate final reports while at least one required section is `INCOMPLETE`.
- Re-request only failed sections and re-run validation.

6. Compile reports.
- Use `scripts/compile_report.py` to build deterministic outputs.
- Require exactly three markdown outputs:
  - `server-security-report.md`
  - `server-performance-report.md`
  - `executive-summary-and-priorities.md`

## Input Contract

Provide a JSON document with:

- `scope`: `int/data | int/assess | custom`
- `source`: `live_sql | section_summaries`
- `audit_mode`: defaults to `read_only`
- `server`: server label for report headers
- `sections`: required section payloads (list or object map)

Optional:

- `input_sections`: raw fallback section summaries before normalization

## Output Contract

Always emit three markdown artifacts after successful validation:

1. `Server Security Report`
2. `Server Performance Report`
3. `Executive Summary + Prioritized Recommendations`

If validation fails, stop synthesis and return explicit failed section ids and reasons.

## Script Usage

Compile from JSON input:

```bash
python scripts/compile_report.py --input /path/to/audit-input.json --output-dir /path/to/out
```

Expected behavior:

- Exit non-zero on missing required sections or incomplete/truncated content.
- Exit zero only when all three reports are generated.

## References

- Read `references/audit-playbook.md` for section SQL checklist, severity thresholds, and categorization rules.

