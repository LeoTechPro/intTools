## ADDED Requirements

### Requirement: No implicit Codex-home fallback reads
Repo-owned intTools tooling MUST NOT automatically read secrets, governance runtime state, or session files from Codex home (`$CODEX_HOME`, `~/.codex`, or `C:\Users\intData\.codex`) as a fallback.

#### Scenario: Governance runtime starts
- **WHEN** `lockctl` or `gatesctl` initializes without an explicit state-dir override
- **THEN** it uses `/int/tools/.runtime/**`
- **AND** it does not enumerate or copy legacy state from Codex-home memories

#### Scenario: Secret-backed helper starts
- **WHEN** an intTools helper needs a local env file
- **THEN** it reads the configured runtime secrets root or explicit env-file path
- **AND** it does not fall back to `$CODEX_HOME/var` or `~/.codex/var`

#### Scenario: Session memory tool reads Codex sessions
- **WHEN** an IntBrain session-memory tool reads local Codex/OpenClaw sessions
- **THEN** the caller supplies an explicit `codex_home` or concrete session `file`
- **AND** absent explicit input is rejected instead of probing the native Codex home
