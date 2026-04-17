## 1. Spec

- [x] 1.1 Add OpenSpec change package for publishing `cabinet` and `mempalace` in `IntData Tools`.
- [x] 1.2 Add process spec delta for memory plugin packaging/catalog parity.

## 2. Implementation

- [x] 2.1 Add `codex/plugins/cabinet` package (`plugin.json` + `.mcp.json`).
- [x] 2.2 Add `codex/plugins/mempalace` package (`plugin.json` + `.mcp.json`).
- [x] 2.3 Register `cabinet` and `mempalace` in `.agents/plugins/marketplace.json`.
- [x] 2.4 Update README `IntData Tools Codex Plugins` section.

## 3. Validation

- [x] 3.1 Validate JSON manifests (`marketplace.json`, plugin manifests, `.mcp.json`).
- [x] 3.2 Verify package path presence for new marketplace entries.
- [x] 3.3 Run local MCP smoke (`initialize` + `tools/list`) for `cabinet_fs` and `mempalace`.
- [ ] 3.4 Sync `/int/tools` to `vds.intdata.pro` and verify catalog parity.
