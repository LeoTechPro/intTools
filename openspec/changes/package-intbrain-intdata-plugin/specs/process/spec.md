## ADDED Requirements

### Requirement: IntData Tools Codex plugins MUST be packaged and cataloged consistently
The system MUST expose repo-owned Codex plugin integrations through packaged plugin manifests and the `IntData Tools` marketplace when they are intended for Codex App plugin installation.

#### Scenario: Repo-owned MCP integration is promoted to Codex App plugin
- **WHEN** a repo-owned MCP integration is intended to appear under `IntData Tools` in Codex App
- **THEN** it has a tracked `.codex-plugin/plugin.json` manifest
- **AND** it has a tracked plugin MCP config
- **AND** it is listed in `.agents/plugins/marketplace.json`
- **AND** marketplace policy uses `INSTALLED_BY_DEFAULT` installation and `ON_INSTALL` authentication unless the owner explicitly specifies another policy
