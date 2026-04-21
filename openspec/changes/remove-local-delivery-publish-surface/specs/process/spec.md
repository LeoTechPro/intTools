## REMOVED Requirements

### Requirement: Local delivery publish wrappers are canonical
The system MUST route repo-owned publish and deploy capabilities through canonical engines under `delivery/bin`.

#### Scenario: Agent resolves a local publish intent
- **WHEN** an agent resolves a publish or deploy intent for `/int/*`
- **THEN** the routing registry returns a repo-owned `delivery/bin/publish_*` engine or adapter

## ADDED Requirements

### Requirement: Local delivery publish wrappers are not provided
The system MUST NOT provide repo-owned `delivery/bin/publish_*` engines, legacy `codex/bin/publish_*.ps1` shims, or an `intdata-control` MCP `publish` tool.

#### Scenario: Agent needs to publish a repository
- **WHEN** the owner explicitly asks an agent to push, publish, deploy, or выкатывать a repository
- **THEN** the agent uses explicit native commands and the repository's current documented process
- **AND** the agent does not route through `/int/tools/delivery/bin/publish_*`, `/int/tools/codex/bin/publish_*.ps1`, or `mcp__intdata_control__.publish`

#### Scenario: Agent validates the intData Control MCP surface
- **WHEN** `intdata-control` tools are listed from a fresh MCP process
- **THEN** no tool named `publish` is present
- **AND** sync-gate, routing, gate receipts, commit binding, OpenSpec, and lockctl tools remain available

#### Scenario: Agent validates high-risk routing
- **WHEN** the high-risk routing registry is validated
- **THEN** no `publish_*` or `deploy:*` local delivery capability is present
- **AND** stale publish wrapper paths are rejected from active docs and skills
