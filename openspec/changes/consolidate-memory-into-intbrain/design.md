# Design

## Current State
`intmemory` is a Codex-session sidecar that parses local Codex session JSONL, redacts secrets, derives repo/session tags, deduplicates by `source_hash`, writes to IntBrain `context/store`, and searches via IntBrain retrieval. MemPalace is packaged as a separate MCP plugin pointing to `D:/int/mempalace/.venv/Scripts/python.exe -m mempalace.mcp_server`.

Cabinet is currently a separate local product repo under `D:/int/cabinet` and is exposed to Codex through a dedicated filesystem MCP plugin. Because it is a product contour, not just a thin plugin wrapper, physical deletion requires a count-check and explicit recorded acceptance after IntBrain import coverage exists.

## Target State
`intbrain` owns all repo-managed memory/context operations. Imported session, MemPalace, and Cabinet items are stored through IntBrain context APIs with explicit source names and traceable metadata. No old MCP names remain.

## Interface
New `intbrain` MCP tools:
- `intbrain_memory_sync_sessions`: import Codex/OpenClaw session JSONL into IntBrain; supports `owner_id`, `codex_home`, `source_root`, `since`, `file`, `incremental`, `dry_run`.
- `intbrain_memory_search`: search imported memory items through IntBrain retrieval; supports `owner_id`, `query`, `limit`, `days`, `repo`.
- `intbrain_memory_recent_work`: summarize recent in-scope local session files without requiring remote writes.
- `intbrain_memory_session_brief`: summarize one session by id.
- `intbrain_memory_import_mempalace`: inventory/import MemPalace palace files; supports `owner_id`, `palace_root`, `dry_run`, `limit`.
- `intbrain_cabinet_inventory`: inventory Cabinet workspace/runtime data before product absorption; supports `cabinet_root`, `limit`.
- `intbrain_cabinet_import`: dry-run or import Cabinet workspace/runtime data into IntBrain; supports `owner_id`, `cabinet_root`, `dry_run`, `limit`.

## Migration and Removal
Migration is count-check based. Dry-run reports candidate counts and source names. Live import writes only through IntBrain. Runtime deletion is allowed only after the count-check result is recorded in INT-222. Historical OpenSpec packages remain untouched.

Cabinet plugin removal is allowed after the IntBrain Cabinet inventory/import path exists. Physical removal of `D:/int/cabinet` is blocked until a successful live import or an explicit recorded owner acceptance confirms no separate Cabinet product state remains.

## Failure Modes
- Missing IntBrain credentials: read-only local summaries still work; write/search operations return explicit config errors.
- Missing MemPalace palace: import reports zero candidates and does not block repo cleanup.
- Existing Cabinet product repo: plugin surface can be removed, but product directory deletion is blocked until count-check and acceptance are recorded.
- Dirty tree baseline: INT-222 records owner approval to work over existing dirty state; unrelated baseline changes are not reverted.
