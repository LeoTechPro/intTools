## ADDED Requirements

### Requirement: IntData Tools memory plugins MUST be packaged and cataloged through repo source-of-truth
When memory-related plugins are exposed in `IntData Tools`, they MUST be represented as tracked plugin packages and marketplace entries in `/int/tools`.

#### Scenario: Cabinet or MemPalace is published in IntData Tools
- **WHEN** `cabinet` or `mempalace` is intended to appear in the `IntData Tools` family
- **THEN** each plugin has a tracked `codex/plugins/<plugin>/.codex-plugin/plugin.json`
- **AND** each plugin has a tracked `codex/plugins/<plugin>/.mcp.json`
- **AND** each plugin is listed in `.agents/plugins/marketplace.json`
- **AND** marketplace policy uses `INSTALLED_BY_DEFAULT` + `ON_INSTALL` unless the owner explicitly approves another policy

### Requirement: IntData Tools catalog updates MUST keep local and VDS checkouts aligned
Catalog and package changes for `IntData Tools` MUST be synchronized across managed local and VDS `/int/tools` checkouts to avoid family/plugin drift.

#### Scenario: Plugin catalog is changed in local `/int/tools`
- **WHEN** local `/int/tools` changes plugin packaging or `.agents/plugins/marketplace.json`
- **THEN** `vds.intdata.pro:/int/tools` receives the same catalog/package state after validation
- **AND** both checkouts expose the same plugin names for the changed scope
