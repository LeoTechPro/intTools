# Change: Consolidate intTools plugin surfaces V1 (INT-222)

## Why
`/int/tools` currently exposes overlapping memory/product contours and duplicated control/runtime plugin surfaces. `intbrain`, `intmemory`, MemPalace, and Cabinet overlap across agent memory, workspace context, and local product context. `lockctl`, `multica`, `openspec`, and `intdata-governance` are separate packaged plugins around one control-plane. `intdata-vault` is a standalone runtime-adjacent plugin even though its tools belong with `intdata-runtime`.

The owner explicitly directed a hard cutover with no compatibility aliases, selected `intdata-control` / `intData Control` as the aggregate control plugin, selected `Developer Tools` as the active marketplace category, and directed Cabinet absorption into IntBrain as a product capability where feasible.

## What Changes
- Make `intbrain` the only repo-owned memory/context surface in IntData Tools.
- Move useful `intmemory` session parsing, sanitization, dedup, recent-work, search, and session-brief capabilities into the `intbrain` profile.
- Add an IntBrain-owned import/count-check path for MemPalace palace data before runtime deletion.
- Add IntBrain-owned Cabinet inventory/import paths and remove the active Cabinet plugin surface after count-check.
- Remove repo-owned `intmemory` CLI/MCP entrypoints and `mempalace` plugin/catalog entries.
- Add `intdata-control` as the only active control-plane plugin for lockctl, Multica, OpenSpec, routing, gates, and publication tools.
- Move vault tools into `intdata-runtime` and remove the `intdata-vault` plugin surface.
- Replace per-profile Firefox wrapper clutter with a registry-backed launcher.
- Categorize active intTools plugins as `Developer Tools`.
- Remove local and VDS runtime/config references after migration count-check succeeds.

## Out of Scope
- Removing `mcp-obsidian-memory`, lockctl engine code, or gatesctl engine code.
- Rewriting historical OpenSpec change packages.
- Keeping deprecated `intmemory_*`, `mempalace_*`, or `mcp-intmemory*` aliases.
- Removing `intdb` as a separate plugin.
- Physically deleting `D:/int/cabinet` before Cabinet inventory/import count-check and recorded owner acceptance.

## Acceptance
- `mcp-intdata-cli.py --profile intbrain` exposes the migrated memory tools.
- Old `intmemory`/`mempalace` MCP/plugin surfaces are absent from active repo catalog and config templates.
- `mcp-intdata-cli.py --profile intdata-control` exposes the former lockctl, Multica, OpenSpec, and governance tools.
- `mcp-intdata-cli.py --profile intdata-runtime` exposes host/SSH/browser runtime tools plus vault sanitizer/GC tools.
- Old plugin IDs `lockctl`, `multica`, `openspec`, `intdata-governance`, `intdata-vault`, and `mempalace` are absent from the active marketplace.
- `cabinet` is absent from the active marketplace after IntBrain Cabinet inventory/import tools exist.
- Active marketplace entries use `Developer Tools`.
- Browser profile launch resolves from `codex/config/browser-profiles.v1.json`.
- Migration dry-run/count-check can inventory local Codex sessions, MemPalace palace data, and Cabinet workspace/runtime data.
- Runtime cleanup removes local `D:/int/mempalace` and `mempalace@int-tools` config entries after count-check.
- VDS cleanup is performed only where traces exist.
