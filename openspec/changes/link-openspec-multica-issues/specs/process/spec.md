## ADDED Requirements

### Requirement: OpenSpec changes MUST link to Multica issues
The system MUST keep tracked `/int/tools` OpenSpec change packages explicitly
linked to their Multica execution issue.

#### Scenario: Tracked tooling change is prepared
- **WHEN** a tracked tooling/process mutation is prepared under
  `openspec/changes/<change-id>/`
- **THEN** the change package names the owning Multica issue in `INT-*` format
- **AND** the Multica issue or worklog names the OpenSpec change path

### Requirement: OpenSpec and Multica MUST keep separate source-of-truth roles
The system MUST use OpenSpec as the requirements/spec/acceptance source-of-truth
and Multica as the execution/worklog/status source-of-truth.

#### Scenario: Change context is recorded in Multica
- **WHEN** a Multica issue records context for an OpenSpec-backed change
- **THEN** it includes a short summary and OpenSpec path links
- **AND** it does not mirror full OpenSpec proposal/spec/task content as a
  second source-of-truth
- **AND** if one `INT-*` issue owns several OpenSpec changes, each change path is
  named explicitly
