## MODIFIED Requirements

### Requirement: Guardrail entrypoints use canonical custom roles

Tracked `intdb` entrypoints MUST expose the active canonical role matrix for operator access.

#### Scenario: admin wrappers use `agents`

- **WHEN** an operator uses the tracked `punktb-prod-admin` or `intdata-dev-admin` entrypoint
- **THEN** the entrypoint MUST target role `agents`
- **AND** the database target MUST remain unchanged

#### Scenario: legacy readonly wrapper uses `db_readonly_prod`

- **WHEN** an operator uses the tracked `punktb-legacy-ro` entrypoint
- **THEN** the entrypoint MUST target role `db_readonly_prod`
- **AND** the database target MUST remain `punkt_b_legacy_prod`

#### Scenario: tracked docs advertise only canonical active roles

- **WHEN** current `intdb` and active Punkt-B access runbooks describe operator entrypoints
- **THEN** they MUST describe `agents` as the canonical tracked admin role
- **AND** they MUST describe `db_readonly_prod` as the tracked readonly role for `punkt_b_legacy_prod`
- **AND** they MUST NOT instruct operators to use `db_admin_prod`, `db_admin_dev`, or `db_readonly_legacy` in active paths
