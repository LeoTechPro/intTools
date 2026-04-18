## ADDED Requirements

### Requirement: Agents MUST use MCP plugin tools before direct CLIs
Agents running in MCP-enabled Codex/OpenClaw runtimes MUST use the installed MCP plugin tools as the primary interface for governed repo-owned tooling whenever the matching plugin surface is available.

#### Scenario: Agent needs OpenSpec operations
- **WHEN** an agent needs to list, show, validate, inspect status, create, update, or archive OpenSpec artifacts
- **AND** the OpenSpec MCP plugin tools are available
- **THEN** the agent uses the OpenSpec plugin tool surface such as `mcp__openspec__.openspec_list`, `mcp__openspec__.openspec_show`, `mcp__openspec__.openspec_validate`, `mcp__openspec__.openspec_new`, `mcp__openspec__.openspec_change`, `mcp__openspec__.openspec_spec`, or `mcp__openspec__.openspec_archive`
- **AND** the agent MUST NOT call `openspec`, `codex/bin/openspec`, `codex/bin/openspec.ps1`, or `codex/bin/openspec.cmd` merely because `openspec` is not present in `PATH`

#### Scenario: Agent needs Multica issue operations
- **WHEN** an agent needs to list, search, get, create, update, assign, comment on, or change status for Multica issues
- **AND** the Multica MCP plugin tools are available
- **THEN** the agent uses the Multica plugin tool surface such as `mcp__multica__.multica_issue`
- **AND** the agent MUST NOT call `multica issue ...` directly as a fallback while the plugin tool surface is available

#### Scenario: Plugin tool is unavailable or blocked
- **WHEN** the matching MCP plugin surface is unavailable or returns a tool-level blocker for the required operation
- **THEN** the agent stops or reports the blocker before using a direct CLI or repo-local wrapper fallback
- **AND** any direct CLI or wrapper fallback requires explicit owner approval
- **AND** the agent records the attempted plugin tool, the error/blocker, and the reason the fallback was necessary in the Multica worklog or handoff

### Requirement: CLI wrappers MUST remain operator and adapter paths
Repo-local CLI wrappers for governed tooling MUST remain documented as versioned operator, compatibility, or MCP-server adapter entrypoints, not as the preferred agent interface when a matching MCP plugin tool is available.

#### Scenario: Documentation lists OpenSpec or Multica wrappers
- **WHEN** repo documentation lists `codex/bin/openspec*`, `mcp-intdata-cli.* --profile openspec`, `mcp-intdata-cli.* --profile multica`, or direct `multica` commands
- **THEN** the documentation distinguishes those paths from the agent-facing MCP plugin tool calls
- **AND** it states that agents in MCP-enabled runtimes use the plugin tools first

### Requirement: Lock issue metadata MUST be optional and support Multica identifiers
The lock runtime MUST allow file locks without issue metadata, and MUST accept full Multica `INT-*` identifiers when issue metadata is supplied.

#### Scenario: Lock is acquired outside an issue-bound task
- **WHEN** an agent or operator acquires or queries a file lock for work that is not yet attached to a Multica issue
- **THEN** the lock operation succeeds without an `issue` value
- **AND** the lock remains filterable by repo, path, owner, and state

#### Scenario: Lock is acquired for a Multica issue
- **WHEN** an agent or operator supplies issue metadata for a Multica-linked task
- **THEN** the lock runtime accepts the full `INT-*` identifier, such as `INT-224`
- **AND** the runtime MUST NOT require agents to truncate the identifier to its numeric suffix

#### Scenario: Legacy numeric lock issue id is used
- **WHEN** existing scripts or operators supply a legacy numeric issue id
- **THEN** the lock runtime continues to accept that numeric id for compatibility
