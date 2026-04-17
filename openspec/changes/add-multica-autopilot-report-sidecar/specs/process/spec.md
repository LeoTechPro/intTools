## ADDED Requirements

### Requirement: Autopilot report delivery MUST fail closed without target mapping
The tooling MUST NOT create new Multica issues when an autopilot report target is not configured.

#### Scenario: Missing autopilot target mapping
- **WHEN** a sidecar run is requested for an autopilot id that is not mapped to a master issue
- **THEN** the run exits with an explicit configuration error
- **AND** it does not create a Multica issue
- **AND** it does not create a Multica comment
- **AND** it does not enqueue a Telegram outbox row

### Requirement: Autopilot report delivery MUST use existing Multica and Probe boundaries
The tooling MUST deliver autopilot report comments through the existing Multica comment interface and Telegram copies through the existing Probe outbox interface.

#### Scenario: Configured delivery succeeds
- **WHEN** an autopilot id has a configured master issue
- **AND** a new dedupe key has not been fully delivered
- **THEN** the sidecar posts the rendered report as a Multica issue comment
- **AND** it enqueues a Telegram copy through Probe outbox
- **AND** it records completed delivery phases in external runtime state

### Requirement: Autopilot report delivery MUST dedupe phase retries
The tooling MUST avoid duplicate comments or Telegram outbox rows for the same dedupe key.

#### Scenario: Comment already posted but Telegram failed
- **WHEN** runtime state records that the comment phase is complete
- **AND** the Telegram phase is not complete
- **THEN** the sidecar skips comment creation
- **AND** retries only the Telegram outbox enqueue
