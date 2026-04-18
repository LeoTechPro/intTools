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

### Requirement: OpenSpec changes MUST link to Multica issues
The system MUST keep tracked `/int/tools` OpenSpec change packages explicitly linked to their Multica execution issue.

#### Scenario: Tracked tooling change is prepared
- **WHEN** a tracked tooling/process mutation is prepared under `openspec/changes/<change-id>/`
- **THEN** the change package names the owning Multica issue in `INT-*` format
- **AND** the Multica issue or worklog names the OpenSpec change path

### Requirement: OpenSpec and Multica MUST keep separate source-of-truth roles
The system MUST use OpenSpec as the requirements/spec/acceptance source-of-truth and Multica as the execution/worklog/status source-of-truth.

#### Scenario: Change context is recorded in Multica
- **WHEN** a Multica issue records context for an OpenSpec-backed change
- **THEN** it includes a short summary and OpenSpec path links
- **AND** it does not mirror full OpenSpec proposal/spec/task content as a second source-of-truth
- **AND** if one `INT-*` issue owns several OpenSpec changes, each change path is named explicitly

### Requirement: Owner-directed publication MUST NOT be filtered by agent judgment
The system MUST treat an explicit owner command to `push/publish/выкатывай/публикуй` as a directive to publish the already prepared publication-state as-is, unless a blocker or ambiguity is reported back to the owner first.

#### Scenario: Explicit publication command is received
- **WHEN** the owner explicitly orders `push`, `publish`, `выкатывай`, or `публикуй`
- **THEN** the agent may still prepare a local commit according to the agreed implementation scope unless the owner instructed otherwise
- **AND** the agent publishes the already prepared publication-state through the canonical flow for that repo or stops and asks the owner for instructions if a blocker or ambiguity exists
- **AND** the agent does not autonomously shrink the publication scope to "only its own" or "only relevant" changes

#### Scenario: Foreign or unattributed changes are present during publication
- **WHEN** explicit owner-directed publication is requested and the prepared publication-state contains foreign, unattributed, or previously existing changes
- **THEN** the agent MUST NOT exclude, stash, revert, hide, or defer those changes from the publication-state on its own authority merely because it considers them not its own
- **AND** any need to exclude part of the state is escalated back to the owner as an explicit decision

### Requirement: Existing process capability is extended by default
The system MUST extend existing tooling governance capability specs by default and MUST NOT create parallel capability directories for the same process scope without explicit owner approval.

#### Scenario: Tooling governance already has a matching process spec
- **WHEN** a new change affects the existing tooling governance process
- **THEN** the agent updates the existing `process` capability spec rather than creating a duplicate capability directory

### Requirement: OpenSpec CLI entrypoints MUST be tracked and cross-platform
The system MUST keep repo-managed OpenSpec entrypoints in git for Linux and Windows runtimes so the local OpenSpec CLI can be launched consistently from both platforms.

#### Scenario: OpenSpec CLI is invoked from Linux or Windows
- **WHEN** an operator or agent uses the repo-managed OpenSpec launcher from Linux or Windows
- **THEN** a tracked entrypoint exists for the target platform in `codex/bin/`
- **AND** that entrypoint forwards to the locally installed OpenSpec CLI or returns an explicit install error instead of relying on ad-hoc machine-local wrappers
