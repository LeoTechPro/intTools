## 1. OPENSPEC
- [x] 1.1 Create the change package for plugin-first OpenSpec/Multica access.
- [x] 1.2 Add a `process` spec delta for MCP plugin-first agent tool access.

## 2. GOVERNANCE DOCS AND SKILLS
- [x] 2.1 Update `AGENTS.md` with plugin-first agent access rules.
- [x] 2.2 Update `openspec/AGENTS.md` with OpenSpec MCP plugin-first instructions.
- [x] 2.3 Update `README.md` so CLI wrappers are documented as operator/adapter paths, not agent fallback.
- [x] 2.4 Harden packaged `openspec` and `multica` plugin skills.
- [x] 2.5 Update managed Codex `agent-issues` skill assets away from GitHub/CLI fallback language.
- [x] 2.6 Fix `lockctl` issue metadata handling so `issue` is optional and full `INT-*` ids are accepted.

## 3. VALIDATION
- [x] 3.1 Validate the OpenSpec change with the OpenSpec MCP plugin.
- [x] 3.2 Grep the touched instructions for stale direct CLI fallback wording.
- [x] 3.3 Confirm unrelated untracked `consolidate-memory-into-intbrain` remains untouched.
- [x] 3.4 Run focused `lockctl` unit tests.

### Blockers / Notes
- `sync_gate start` was blocked by pre-existing untracked `openspec/changes/consolidate-memory-into-intbrain/`; owner explicitly approved working around that dirty tree without touching or staging it.
- Initial `lockctl` MCP calls accepted only numeric issue ids; the implementation is updated in this change to accept optional issue metadata and full `INT-*` ids.
- The already-running `lockctl` MCP server in this session still has the old module loaded and must be restarted before it accepts `INT-*` at runtime.
