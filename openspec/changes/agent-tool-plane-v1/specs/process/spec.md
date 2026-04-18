## ADDED Requirements

### Requirement: Int-tools plugin tools MUST have capability-level skill coverage
Every MCP tool exposed by an `int-tools` plugin MUST be covered by exactly one capability skill that explains when to use it, required inputs, guardrails, blockers, fallback policy, and example calls.

#### Scenario: Agent chooses a plugin tool
- **WHEN** an agent task maps to an int-tools MCP capability
- **THEN** a capability skill exists for the relevant tool group
- **AND** the root plugin skill routes the agent to that capability skill
- **AND** the tool is not documented only in a broad plugin-level skill

### Requirement: Int-tools plugin and app surfaces MUST be verifiable
The repository MUST include a verifier that checks plugin manifests, marketplace entries, MCP protocol smoke, expected tool counts, skill coverage, and negative mutation guard behavior.

#### Scenario: Plugin verification runs
- **WHEN** the verifier is executed in `/int/tools`
- **THEN** it validates the four int-tools plugin profiles
- **AND** it fails if a tool is missing capability skill coverage
- **AND** it fails if guarded high-risk tools accept missing mutation confirmation

### Requirement: Remote ChatGPT app exposure MUST be curated
The remote ChatGPT Apps/Connectors surface for int-tools MUST expose a curated tool-only MCP app in v1 and MUST NOT publish the whole local control-plane surface by default.

#### Scenario: Remote app v1 is designed
- **WHEN** int-tools capabilities are exposed through a remote MCP endpoint
- **THEN** read/search tools are preferred for knowledge retrieval
- **AND** write or control actions are explicitly selected, annotated, authenticated, logged, and owner-approved
- **AND** production secrets remain outside tracked git
