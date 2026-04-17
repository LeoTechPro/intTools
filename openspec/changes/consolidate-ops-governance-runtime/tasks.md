## 1. Spec

- [x] 1.1 Create OpenSpec change package for governance/runtime consolidation.
- [x] 1.2 Define hard-cutover interface and guard expectations.

## 2. Implementation

- [x] 2.1 Update marketplace plugin entries (remove 6 old, add 2 new).
- [x] 2.2 Add new packaged plugins (`intdata-governance`, `intdata-runtime`).
- [x] 2.3 Remove old packaged plugins and old launchers.
- [x] 2.4 Refactor shared MCP wrapper profiles/tool surface.
- [x] 2.5 Update README docs and migration notes.
- [x] 2.6 Update local Codex plugin enablement config.

## 3. Validation

- [x] 3.1 Validate Python and JSON artifacts.
- [x] 3.2 Validate OpenSpec package (`openspec validate ... --strict`).
- [x] 3.3 Smoke `initialize` + `tools/list` for both new plugins.
- [x] 3.4 Verify mutation guard rejections for mutating tools.
- [x] 3.5 Verify old plugin IDs/tool names are absent.
