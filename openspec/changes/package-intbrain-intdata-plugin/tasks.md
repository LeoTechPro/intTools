## 1. Spec

- [x] 1.1 Add OpenSpec change package for IntBrain plugin packaging.
- [x] 1.2 Define marketplace policy and scope boundaries.

## 2. Implementation

- [x] 2.1 Add `codex/plugins/intbrain` plugin manifest, MCP config, and skill pointer.
- [x] 2.2 Add `codex/bin/mcp-intbrain.cmd` Windows launcher.
- [x] 2.3 Register `intbrain` in `.agents/plugins/marketplace.json`.
- [x] 2.4 Set all IntData Tools entries to `INSTALLED_BY_DEFAULT` + `ON_INSTALL`.
- [x] 2.5 Update README entrypoint/plugin documentation.

## 3. Validation

- [x] 3.1 Validate JSON manifests.
- [x] 3.2 Verify launcher missing-env behavior.
- [x] 3.3 Smoke MCP `initialize` and `tools/list` when IntBrain env is available.
