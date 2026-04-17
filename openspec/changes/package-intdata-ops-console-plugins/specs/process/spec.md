## ADDED Requirements

### Requirement: IntData Tools ops capabilities MUST be packaged as explicit Codex plugins
The system MUST expose owner-approved reusable ops capabilities through separate Codex plugin packages when they are intended to be installed and used from Codex App.

#### Scenario: Ops capability is exposed in IntData Tools
- **WHEN** a repo-owned ops capability is added to the `IntData Tools` marketplace
- **THEN** it has a tracked plugin package with `.codex-plugin/plugin.json`
- **AND** it has a tracked `.mcp.json` when it exposes tools
- **AND** its marketplace policy is `INSTALLED_BY_DEFAULT` with `ON_INSTALL` authentication unless the owner explicitly approves a different policy

### Requirement: CLI-backed MCP wrappers MUST use structured commands and mutation guards
The system MUST NOT expose arbitrary shell execution through IntData Tools MCP wrappers.

#### Scenario: A CLI-backed MCP tool runs
- **WHEN** a plugin wraps a repo-owned or installed CLI
- **THEN** the wrapper accepts structured command names and argument arrays
- **AND** it runs subprocesses without shell string evaluation
- **AND** write, publish, archive, status-changing, daemon-control, bootstrap, or destructive commands require `confirm_mutation=true`
- **AND** those mutating calls also require an `issue_context` matching `INT-*`
