## ADDED Requirements

### Requirement: Active int-tools plugins MUST support Russian user-facing descriptions
Active `int-tools` plugin manifests and plugin skill cards MUST provide Russian user-facing text.

#### Scenario: Plugin metadata localization
- **WHEN** plugin metadata is read from active `plugin.json` manifests
- **THEN** fields `description`, `interface.shortDescription`, and `interface.longDescription` are Russian
- **AND** technical metadata and identifiers remain unchanged

#### Scenario: Plugin skill instructions are self-contained
- **WHEN** a plugin skill card is opened or activated from the plugin UI
- **THEN** `codex/plugins/*/skills/SKILL.md` contains direct operational instructions for that plugin
- **AND** the skill body does not only point to another out-of-plugin skill path

### Requirement: Localization rollout MUST NOT alter plugin/runtime contracts
Description and skill-instruction localization MUST be text-only and MUST NOT modify runtime/profile/tool contracts.

#### Scenario: No runtime contract drift
- **WHEN** localization change is applied
- **THEN** plugin IDs, display names, MCP tool names, and launcher/profile wiring are unchanged
