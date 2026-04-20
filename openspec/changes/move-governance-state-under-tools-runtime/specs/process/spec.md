## ADDED Requirements

### Requirement: intTools governance runtime MUST stay outside Codex memories
The intTools governance runtime state for `lockctl` and `gatesctl` MUST default to `/int/tools/.runtime/**` and MUST NOT default to `$CODEX_HOME/memories/**` or `~/.codex/memories/**`.

#### Scenario: lockctl resolves its default state
- **WHEN** `LOCKCTL_STATE_DIR` is not set
- **THEN** `lockctl` resolves its state directory to `/int/tools/.runtime/lockctl`
- **AND** `$CODEX_HOME` does not affect that default

#### Scenario: gatesctl resolves its default state
- **WHEN** `GATESCTL_STATE_DIR` is not set
- **THEN** `gatesctl` resolves its state directory to `/int/tools/.runtime/gatesctl`
- **AND** `$CODEX_HOME` does not affect that default

### Requirement: explicit governance state overrides MUST remain supported
The intTools governance runtimes MUST continue to honor explicit state directory environment overrides for operators and tests.

#### Scenario: explicit state override is set
- **WHEN** `LOCKCTL_STATE_DIR` or `GATESCTL_STATE_DIR` is set
- **THEN** the matching tool uses that explicit state directory

### Requirement: legacy Codex-memory governance state MUST migrate non-destructively
Legacy governance state under `.codex/memories/{lockctl,gatesctl}` MAY be copied into `/int/tools/.runtime/**`, but migration MUST NOT delete or move the legacy source directory.

#### Scenario: legacy state exists
- **WHEN** legacy `lockctl` or `gatesctl` state exists under Codex memories
- **THEN** missing files are copied into the matching `/int/tools/.runtime/**` directory
- **AND** a migration marker is written in the new runtime directory
- **AND** the legacy source directory remains in place
