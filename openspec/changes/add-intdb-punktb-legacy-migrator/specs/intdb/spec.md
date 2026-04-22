## ADDED Requirements

### Requirement: intdb MUST provide a project data migrator core
The system MUST provide an `intdb` project migration workflow that can read from one configured PostgreSQL profile and write to another configured PostgreSQL profile with explicit dry-run and apply modes.

#### Scenario: Operator rehearses a project data migration
- **WHEN** the operator runs a project migration in dry-run mode
- **THEN** `intdb` reads source data through the source profile
- **AND** stages target changes through the target profile
- **AND** rolls back target changes before exit
- **AND** reports source, merged entity, staged result, and mode counts

#### Scenario: Operator applies a project data migration
- **WHEN** the operator runs a project migration in apply mode
- **THEN** `intdb` requires target approval matching the target profile
- **AND** prod-class target profiles require the existing prod force flag
- **AND** source sessions remain read-only

### Requirement: intdb MUST support PunktB legacy assessment migration
The system MUST provide a PunktB legacy assessment migration workflow from `punkt_b_legacy_prod.public.clients` / `public.managers` / `public.diagnostics` into the current target assessment schema.

#### Scenario: Legacy clients are migrated
- **WHEN** legacy clients contain numeric ids and target clients use UUID ids
- **THEN** the migrator MUST identify target clients by normalized email
- **AND** numeric legacy ids MUST be stored only as import metadata
- **AND** repeated runs MUST NOT create duplicate clients for the same normalized email

#### Scenario: Legacy source has duplicate client emails
- **WHEN** multiple legacy client rows share the same normalized email
- **THEN** the migrator MUST merge them into one target client
- **AND** diagnostic results from all duplicate legacy client rows MUST attach to that target client

#### Scenario: Legacy JSONB results are migrated
- **WHEN** a legacy client row has `results` JSONB array entries
- **THEN** each result entry MUST become a target diagnostic result row
- **AND** the result payload MUST preserve the legacy `data` object
- **AND** import metadata MUST include legacy client id, legacy result index, diagnostic id, and source fingerprint
- **AND** repeated runs MUST update the same deterministic target result row instead of inserting duplicates
