## ADDED Requirements

### Requirement: Active int-tools plugins MUST use a single MCP runtime engine
All active plugins in the `int-tools` family MUST execute through one shared MCP runtime engine with per-plugin profile selection.

#### Scenario: Plugin entrypoint wiring
- **WHEN** any active `int-tools` plugin is started
- **THEN** its `.mcp.json` launches `codex/bin/mcp-intdata-cli.cmd` (or `.sh`) with `--profile <plugin-id>`
- **AND** the runtime engine is `codex/bin/mcp-intdata-cli.py`
- **AND** dedicated legacy launchers for those plugins are absent

### Requirement: Shared runtime MUST preserve lockctl and intbrain tool contracts
The shared runtime MUST expose the same public MCP tool names and required argument contracts for `lockctl` and `intbrain` as before consolidation.

#### Scenario: Contract parity after migration
- **WHEN** `tools/list` is called for profiles `lockctl` and `intbrain`
- **THEN** the expected public tool names are present without renaming
- **AND** mutating/non-mutating behavior remains compatible with previous wrappers

### Requirement: intbrain profile MUST preserve env/auth behavior
The `intbrain` profile MUST keep existing auth/env semantics and PM date alias handling.

#### Scenario: Missing intbrain agent credentials
- **WHEN** `INTBRAIN_AGENT_ID` or `INTBRAIN_AGENT_KEY` is missing
- **THEN** intbrain calls fail with explicit auth/config error

#### Scenario: PM date aliases
- **WHEN** PM tools receive `date=today|tomorrow|yesterday` (or `due_at=today`)
- **THEN** aliases are coerced to concrete dates/timestamps using provided timezone or default fallback

### Requirement: int-tools catalog MUST expose unified intData branding
Catalog and plugin UI metadata MUST use `intData` branding for family-owned plugins while preserving external product names.

#### Scenario: Branding render in plugin catalog
- **WHEN** plugin metadata is read from marketplace and plugin manifests
- **THEN** family display name is `intData Tools`
- **AND** plugin display names include `intData Locks`, `intData Brain`, `intData DBA`, `intData Governance`, `intData Runtime`, `intData Vault`
- **AND** `Multica` and `OpenSpec` display names remain unchanged
