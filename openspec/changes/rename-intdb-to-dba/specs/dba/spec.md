## ADDED Requirements

### Requirement: DBA contour MUST use `dba` as the canonical tracked identifier
The repository MUST expose the DBA operator contour under the canonical tracked identifier `dba` instead of `intdb`.

#### Scenario: Contour path and engine wiring
- **WHEN** tracked repo-owned paths, router bindings, wrappers, plugin profiles or templates reference the DBA operator contour
- **THEN** they use the identifier `dba`
- **AND** the canonical engine path is rooted under `/int/tools/dba`
- **AND** tracked active references do not require `/int/tools/intdb` as the live contour path

### Requirement: DBA human-facing naming MUST use intDBA
Human-facing short naming for the DBA utility MUST use `intDBA`.

#### Scenario: Short naming in docs and plugin text
- **WHEN** README, runbooks, help text, plugin skills or other human-facing tracked text refer to the DBA utility
- **THEN** the short name is `intDBA`
- **AND** raw `intdb` is not presented as the preferred human-facing utility name

### Requirement: DBA full branding MUST use intData Tools DBA
The full tracked display branding for the DBA utility MUST use `intData Tools DBA`.

#### Scenario: Full display naming
- **WHEN** plugin metadata, catalog text or repo docs render the full DBA utility name
- **THEN** the displayed full name is `intData Tools DBA`
