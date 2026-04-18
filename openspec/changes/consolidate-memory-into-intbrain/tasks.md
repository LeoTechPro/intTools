# Tasks

- [x] 1. Spec and governance
  - [x] 1.1 Add process delta naming `intbrain` as the only repo-owned memory surface.
  - [x] 1.2 Add process delta for `intdata-control`, `intdata-runtime` vault absorption, registry-backed browser profiles, Developer Tools categorization, and Cabinet absorption.
  - [x] 1.3 Validate OpenSpec package.

- [ ] 2. IntBrain memory implementation
  - [x] 2.1 Move reusable session parsing/sanitization/dedup logic into an IntBrain-owned helper module.
  - [x] 2.2 Add `intbrain_memory_sync_sessions`, `intbrain_memory_search`, `intbrain_memory_recent_work`, `intbrain_memory_session_brief`, and `intbrain_memory_import_mempalace` tools to the `intbrain` profile.
  - [x] 2.3 Preserve source traceability with `intbrain.memory.session.v1` and `intbrain.memory.mempalace.v1` source names.
  - [x] 2.4 Add `intbrain_cabinet_inventory` and `intbrain_cabinet_import` tools with Cabinet source traceability.

- [ ] 3. Remove old repo surfaces
  - [x] 3.1 Remove `codex/tools/intmemory/**` and `codex/bin/intmemory*` / `codex/bin/mcp-intmemory*`.
  - [x] 3.2 Remove `codex/plugins/mempalace/**` and marketplace entry.
  - [x] 3.3 Add `intdata-control` plugin/profile and remove old control-plane plugin IDs.
  - [x] 3.4 Move vault tools into `intdata-runtime` and remove `intdata-vault`.
  - [x] 3.5 Replace per-profile Firefox wrappers with registry-backed launch.
  - [ ] 3.6 Update README/config/docs so only canonical plugin surfaces remain.
  - [x] 3.7 Remove `codex/plugins/cabinet/**` and marketplace entry after adding IntBrain Cabinet import.

- [x] 4. Verification and cleanup
  - [x] 4.1 Run unit tests for parser/sanitizer/dedup and MCP tools list smoke.
  - [x] 4.2 Run migration dry-run/count-check locally and on VDS where traces exist.
  - [x] 4.3 Remove local/VDS runtime traces after count-check where deletion is allowed; keep `D:/int/cabinet` blocked until live import/acceptance.
  - [x] 4.4 Record results and risks in INT-222.
