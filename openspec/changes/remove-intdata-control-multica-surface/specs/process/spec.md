## ADDED Requirements

### Requirement: intData Control MUST NOT expose Multica tools
The `intdata-control` MCP profile MUST NOT expose repo-owned Multica tools.

#### Scenario: Agent lists intData Control tools
- **WHEN** an agent or verifier lists tools for the `intdata-control` MCP profile
- **THEN** no tool name starts with `multica_`
- **AND** the removed `multica_issue_write`, `multica_issue_read`, `multica_project_write`, `multica_agent_write`, `multica_skill_write`, `multica_runtime_write`, `multica_config_write`, `multica_daemon_control`, `multica_auth_write`, `multica_attachment_download`, and `multica_repo_checkout` tool names remain forbidden in the active surface

### Requirement: Agents MUST use official Multica interfaces
Agents MUST use the official documented Multica interface for issue state and worklog operations.

#### Scenario: Agent needs Multica issue operations
- **WHEN** an agent needs to list, search, get, create, update, assign, comment on, or change status for Multica issues
- **THEN** the agent uses the official documented `multica` CLI
- **AND** the agent MAY use an official Multica MCP plugin such as `mcp__multica__` when that plugin is installed in the runtime
- **AND** the agent MUST NOT route Multica operations through `intdata-control`

### Requirement: intData Control skills MUST match the active surface
The `intdata-control` plugin skills MUST describe only active `intdata-control` capabilities.

#### Scenario: Plugin skills are verified
- **WHEN** the intTools plugin verifier scans active plugin skills
- **THEN** no active `intdata-control` skill advertises a Multica tool card
- **AND** deleted local Multica tool cards remain removed/forbidden unless they appear only in historical OpenSpec context
