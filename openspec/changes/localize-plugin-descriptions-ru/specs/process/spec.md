## ADDED Requirements

### Requirement: Active int-tools plugins MUST support Russian user-facing descriptions
Active `int-tools` plugin manifests MUST provide Russian text for user-facing description fields.

#### Scenario: Plugin metadata localization
- **WHEN** plugin metadata is read from active `plugin.json` manifests
- **THEN** fields `description`, `interface.shortDescription`, and `interface.longDescription` are Russian
- **AND** technical metadata and identifiers remain unchanged

### Requirement: Localization rollout MUST NOT alter plugin/runtime contracts
Description localization MUST be text-only and MUST NOT modify runtime/profile/tool contracts.

#### Scenario: No runtime contract drift
- **WHEN** localization change is applied
- **THEN** plugin IDs, display names, MCP tool names, and launcher/profile wiring are unchanged
