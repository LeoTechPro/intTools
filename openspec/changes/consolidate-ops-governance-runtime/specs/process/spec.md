## ADDED Requirements

### Requirement: IntData ops plugin catalog MUST expose consolidated governance/runtime surfaces
The `IntData Tools` catalog MUST expose governance and runtime operator capabilities through two aggregated plugin IDs rather than fragmented per-subsystem plugin IDs.

#### Scenario: Governance and runtime plugins are published
- **WHEN** the marketplace is built for IntData Tools
- **THEN** plugin IDs `intdata-governance` and `intdata-runtime` exist
- **AND** plugin IDs `intdata-routing`, `intdata-delivery`, `gatesctl`, `intdata-host`, `intdata-ssh`, and `intdata-browser` are not exposed

### Requirement: Consolidated tools MUST preserve mutation guardrails
Mutating tools in consolidated governance/runtime surfaces MUST enforce explicit mutation confirmation and issue context.

#### Scenario: Mutating consolidated tool is called
- **WHEN** `publish`, `commit_binding`, `host_bootstrap`, `recovery_bundle`, or deprecated compatibility `browser_profile_launch` is called
- **THEN** the wrapper rejects the call unless `confirm_mutation=true`
- **AND** the wrapper rejects the call unless `issue_context` matches `INT-*`
- **AND** new browser-proof work is routed through the `firefox-devtools-testing` workflow.

### Requirement: Consolidation migration is hard-breaking
The consolidation rollout MUST not keep alias compatibility for removed plugin IDs and old tool names.

#### Scenario: Legacy surfaces after cutover
- **WHEN** the consolidated version is active
- **THEN** old plugin IDs are absent from marketplace entries
- **AND** `tools/list` for new plugins does not expose legacy names from removed per-subsystem wrappers
