## ADDED Requirements

### Requirement: Owner-rejected optional IntData Tools plugins MUST be fully de-exposed
When the owner requests removal of an optional IntData Tools plugin, the system MUST remove both marketplace visibility and runnable plugin package exposure.

#### Scenario: Optional plugin is removed from IntData Tools
- **WHEN** an optional plugin is removed from `.agents/plugins/marketplace.json`
- **THEN** its tracked `codex/plugins/<plugin>` package is removed
- **AND** any dedicated MCP launcher for that plugin is removed
- **AND** shared MCP wrapper profile exposure for that plugin is removed
- **AND** unrelated underlying integration scripts are left untouched unless explicitly requested
