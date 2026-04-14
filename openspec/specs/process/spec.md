# process Specification

## Purpose
Требования к тому, как `/int/tools` управляет tracked tooling/process mutations через обязательный OpenSpec lifecycle.

## Requirements
### Requirement: Tracked tooling mutations MUST start from an agreed OpenSpec change
The system MUST require an owner-approved change package in `openspec/changes/<change-id>/` before any tracked mutation of repo-owned tooling/process assets in `/int/tools`.

#### Scenario: Tracked tooling mutation begins
- **WHEN** a task changes tracked wrappers, scripts, hooks, gates, MCP launchers, prompts, rules, skills, publish flows, overlays, repo governance docs, or other repo-owned tooling/process assets
- **THEN** an agreed OpenSpec change package already exists before the first tracked file mutation
- **AND** that package includes `proposal.md`, `tasks.md`, and a relevant spec delta under `specs/**`

### Requirement: Execution MUST block without an active agreed change
The system MUST NOT allow mutate-first execution for tracked tooling/process assets when no active agreed OpenSpec change is defined for the scope.

#### Scenario: Request arrives without active change
- **WHEN** a tracked tooling mutation is requested and no approved `change-id` or agreed spec source-of-truth exists
- **THEN** execution stops before tracked file mutation
- **AND** the owner is asked to approve or identify the required OpenSpec change

### Requirement: Governance docs MUST stay synchronized with OpenSpec source-of-truth
The system MUST keep repo governance docs synchronized with the canonical OpenSpec process spec and active change package whenever tooling governance changes.

#### Scenario: Tooling governance changes
- **WHEN** process rules for tracked tooling mutations are changed
- **THEN** the relevant `openspec/specs/**` and `openspec/changes/**` content is updated together with repo governance docs such as `AGENTS.md` and `README.md`
- **AND** those docs do not become an unsynchronized second source-of-truth

### Requirement: Existing process capability is extended by default
The system MUST extend existing tooling governance capability specs by default and MUST NOT create parallel capability directories for the same process scope without explicit owner approval.

#### Scenario: Tooling governance already has a matching process spec
- **WHEN** a new change affects the existing tooling governance process
- **THEN** the agent updates the existing `process` capability spec rather than creating a duplicate capability directory
