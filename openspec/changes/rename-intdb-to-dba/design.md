# Design: rename intdb contour to dba

## Summary

Rename is split into three layers:

1. Contour/runtime identifiers: `intdb` -> `dba`
2. Human-facing short name: `intDBA`
3. Full display/family name: `intData Tools DBA`

This keeps the repo-owned technical surface compact while making user-facing naming explicit and consistent.

## Decisions

- Filesystem paths, profile ids, router ids, wrapper filenames and canonical engine paths move to `dba`.
- Human-facing prose and plugin labels stop using raw `intdb` and use `intDBA` instead.
- Full plugin/catalog naming becomes `intData Tools DBA`, extending the existing `intData DBA` branding to the requested family name.

## Impact Areas

- OpenSpec canonical spec path currently named `openspec/specs/intdb`
- repo-owned contour path `intdb/**`
- command/router wiring in `codex/bin/mcp-intdata-cli.py`
- plugin profile/config/template ids and tests that currently assert `intdb`
- docs/runbooks and release notes with hardcoded `/int/tools/intdb` paths

## Migration Notes

- Verification must distinguish technical ids that intentionally become `dba` from human-facing prose that must become `intDBA`.
- Historical archived change package names may remain unchanged, but active tracked references inside current source-of-truth should stop depending on `intdb` as the live contour name.
