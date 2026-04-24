## ADDED Requirements

### Requirement: Active process and routing docs MUST point to the dba contour
Tracked process assets that describe current DBA tooling MUST reference the `dba` contour and its renamed entrypoints.

#### Scenario: Current process documentation
- **WHEN** repo-level process docs, runbooks, routing config or verification scripts describe the active DBA contour
- **THEN** they reference `dba`
- **AND** they do not rely on `intdb` as the active contour/profile id

### Requirement: Current branding docs MUST distinguish technical and human-facing names
Tracked process assets MUST keep technical ids and human-facing names consistent during the rename.

#### Scenario: Mixed technical and human-facing references
- **WHEN** a tracked asset contains both a technical identifier and a display name for the DBA contour
- **THEN** the technical identifier is `dba`
- **AND** the human-facing short name is `intDBA`
- **AND** the full display name is `intData Tools DBA`
