## 1. Spec

- [x] 1.1 Create OpenSpec change package for shared runtime + branding cutover.
- [x] 1.2 Define hard-cutover scope, compatibility expectations, and branding targets.

## 2. Implementation

- [x] 2.1 Port `lockctl` profile into `mcp-intdata-cli.py`.
- [x] 2.2 Port `intbrain` profile into `mcp-intdata-cli.py` with existing env/auth behavior.
- [x] 2.3 Add shared launchers `mcp-intdata-cli.cmd` and `mcp-intdata-cli.sh`.
- [x] 2.4 Repoint `.mcp.json` for all 8 active plugins to shared launcher + profile.
- [x] 2.5 Remove legacy dedicated MCP runtimes/launchers for the 8 active plugins.
- [x] 2.6 Apply catalog/plugin branding updates (`intData` style) with Multica/OpenSpec exception.
- [x] 2.7 Update AGENTS/README/routing/layout references affected by removed launchers.

## 3. Validation

- [x] 3.1 Validate Python syntax (`py_compile`) for shared runtime.
- [x] 3.2 Validate JSON artifacts (`plugin.json`, `.mcp.json`, `marketplace.json`, routing/layout policy).
- [x] 3.3 Validate OpenSpec package (`openspec validate ... --strict`).
- [x] 3.4 Smoke `initialize` + `tools/list` for all 8 plugin profiles.
- [x] 3.5 Verify guard behavior for mutating tools and `intbrain` auth error path.
