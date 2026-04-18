---
name: intdb-doctor-status
description: Use for read-only intdb help, doctor, and status diagnostics through the intData DBA MCP wrapper.
---

# intdb: Doctor and Status

Use this for safe DB diagnostics before any migration or SQL work.

## Tools

- `intdata_cli`

## Rules

- Always call with `command="intdb"`.
- Safe examples include `args=["--help"]`, `args=["doctor", ...]`, and status/read-only commands.
- Do not call `intdb.py`, `.ps1`, or `.cmd` directly while MCP is available.

## Blockers

- Unknown DB profile, host, env, or credentials.
- Command is not clearly read-only.

## Fallback

Direct intdb wrappers require MCP blocker and owner approval.

## Examples

- Help: `intdata_cli(command="intdb", args=["--help"])`
- Doctor: `intdata_cli(command="intdb", args=["doctor"])`
- Status: `intdata_cli(command="intdb", args=["migrate", "status"])`
