# Design: Shared MCP runtime for all active int-tools plugins

## Decision

Use one executable surface for plugin entry:

- Engine: `codex/bin/mcp-intdata-cli.py`
- Thin adapters: `codex/bin/mcp-intdata-cli.cmd`, `codex/bin/mcp-intdata-cli.sh`

Each plugin keeps its own plugin ID and installation lifecycle but passes `--profile <plugin-id>` to the shared engine.

## Profile Model

- Existing profiles remain unchanged: `openspec`, `multica`, `intdata-governance`, `intdata-runtime`, `intdb`, `intdata-vault`.
- Added profiles: `lockctl`, `intbrain`.
- Public MCP tool names are preserved for all profiles.

## IntBrain compatibility notes

- Keep env contract:
  - `INTBRAIN_AGENT_ID`
  - `INTBRAIN_AGENT_KEY`
  - `INTBRAIN_CORE_ADMIN_TOKEN`
  - `INTBRAIN_API_BASE_URL`
  - `INTBRAIN_API_TIMEOUT_SEC`
- Keep legacy env-file resolution fallback to `intbrain-agent.env` in runtime/legacy codex secret locations.
- Keep PM date alias coercion (`today|tomorrow|yesterday`) behavior.

## Risk and mitigation

- Risk: stale references to removed launchers.
  - Mitigation: update routing/layout policy and repo docs in the same change.
- Risk: profile regressions after merge.
  - Mitigation: per-profile `initialize` + `tools/list` smoke and targeted behavior checks.
