## ADDED Requirements

### Requirement: intdb MUST provide an owner-gated local Supabase disposable runner
Система MUST предоставлять в `intdb` workflow для локального temporary Supabase runtime, который можно использовать для clean bootstrap и smoke `/int/data`.

#### Scenario: Operator needs clean local backend bootstrap
- **WHEN** owner explicitly requests a clean local disposable backend runtime
- **THEN** `intdb` can create a temporary local Supabase workspace, start the stack, and expose connection info for repo-owned lifecycle

### Requirement: Local disposable runner MUST require explicit owner control confirmation
Система MUST NOT запускать local disposable runner без явного подтверждения owner control.

#### Scenario: Command is launched without confirmation
- **WHEN** operator omits the explicit owner-control confirmation flag
- **THEN** command fails before any Docker/Supabase mutation starts

### Requirement: Local disposable runner MUST apply repo-owned lifecycle on top of Supabase platform layer
Система MUST применять `/int/data` lifecycle поверх локально поднятого Supabase platform layer вместо того, чтобы полагаться на repo-owned bootstrap системных Supabase объектов.

#### Scenario: Local runtime has started
- **WHEN** local Supabase stack is available
- **THEN** `intdb` runs `/int/data/init/010_supabase_migrate.sh apply`
- **AND** applies `init/seed.sql`
- **AND** can optionally run selected SQL smoke files

### Requirement: Retired remote disposable contour MUST NOT be used as fallback
Система MUST NOT fallback from local disposable workflow to retired remote test DB contour.

#### Scenario: Legacy remote disposable path is requested
- **WHEN** operator tries to use retired remote disposable entrypoint or target
- **THEN** tooling returns an explicit retirement error and points to local owner-gated workflow
