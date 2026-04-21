## 1. OpenSpec
- [x] 1.1 Create change package linked to `INT-255`.
- [x] 1.2 Add process spec delta removing `intdata-control` Multica ownership.

## 2. Runtime and verifier
- [x] 2.1 Remove `multica_*` tools and dispatch from `codex/bin/mcp-intdata-cli.py`.
- [x] 2.2 Update plugin verifier counts, mappings, guard cases, and stale-reference checks.
- [x] 2.3 Confirm fresh `intdata-control` `tools/list` exposes no `multica_*` tools.

## 3. Skills and docs
- [x] 3.1 Delete `intdata-control` Multica capability skills.
- [x] 3.2 Update `AGENTS.md`, `README.md`, plugin metadata, plugin router skill, and packaged `agent-issues` source.
- [x] 3.3 Update related OpenSpec and ChatGPT Apps docs.

## 4. Validation
- [x] 4.1 Validate this OpenSpec change strictly.
- [x] 4.2 Run `python scripts/codex/verify_int_tools_plugins.py --report-json`.
- [x] 4.3 Run `python -m unittest agent_plane.tests.test_agent_plane`.
- [x] 4.4 Run focused static checks for removed local Multica tool names.

## Notes
- `sync_gate start` is blocked by a pre-existing dirty tree and ahead state in this checkout; this change is scoped around existing owner state without reverting or stashing unrelated changes.
