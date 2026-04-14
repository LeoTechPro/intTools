## ADDED Requirements

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
