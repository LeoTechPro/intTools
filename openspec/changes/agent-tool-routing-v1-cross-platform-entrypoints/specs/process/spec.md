## ADDED Requirements

### Requirement: High-risk agent intents MUST resolve through approved routing before execution
The system MUST route high-risk agent intents for `/int/*` through an approved logical capability binding before runtime execution starts.

#### Scenario: High-risk intent is requested
- **WHEN** an agent is about to execute `publish/deploy`, `remote access`, `DB apply/smoke/migration diagnostics`, `browser verify/fallback attach`, or `lock/sync gate`
- **THEN** the agent first resolves the request through the approved routing registry
- **AND** execution does not start from an ad-hoc wrapper path chosen without registry resolution

### Requirement: Unsupported or ambiguous high-risk routing MUST block execution
The system MUST block high-risk execution when no supported approved binding exists for the current runtime or when intent resolution is ambiguous.

#### Scenario: Supported binding does not exist
- **WHEN** a high-risk intent has no supported primary binding for the current platform, no approved fallback, no canonical engine, or no matching logical capability
- **THEN** routing returns `blocked` or `ambiguous`
- **AND** the agent does not substitute an unregistered shell wrapper or ad-hoc workaround

### Requirement: Verified skill tools MUST NOT become implicit substitutes for repo-owned high-risk capabilities
The system MUST allow verified skill tools for non-high-risk workflows, but MUST NOT treat them as automatic substitutes for repo-owned high-risk capabilities unless the fallback is explicitly approved in the registry.

#### Scenario: Repo-owned high-risk primary is blocked
- **WHEN** a repo-owned high-risk primary binding cannot be used
- **THEN** the agent may use a verified skill tool only if that tool is declared as an approved fallback in the routing registry
- **AND** otherwise the result stays `blocked`
