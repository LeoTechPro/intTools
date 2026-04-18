## ADDED Requirements

### Requirement: intTools runtime MUST live under the tools checkout
The intTools ops-tooling contour MUST use `/int/tools/.runtime` as the canonical machine-local runtime root for Codex-facing secrets, Firefox MCP state, cloud access state, and related local runtime files.

#### Scenario: Runtime root is resolved by intTools wrappers
- **WHEN** a Codex/OpenClaw wrapper in `/int/tools` needs the default runtime root
- **THEN** it resolves to `/int/tools/.runtime`
- **AND** environment overrides such as `CODEX_RUNTIME_ROOT`, `CODEX_SECRETS_ROOT`, and `CLOUD_ACCESS_ROOT` may still override the default explicitly

### Requirement: repo-local runtime MUST remain untracked
The `/int/tools/.runtime` directory MUST be ignored by git and MUST NOT be used for tracked source, documentation, or generated release artifacts.

#### Scenario: Runtime files are created under the tools checkout
- **WHEN** secrets, browser profiles, logs, run metadata, or cloud runtime files are written under `/int/tools/.runtime`
- **THEN** git does not track them
- **AND** tracked tooling references only documented paths or templates, not live secret file contents

### Requirement: legacy runtime path MUST be transition-only
The old `/int/.runtime` path MAY exist as a local compatibility junction or fallback during migration, but tracked intTools defaults MUST NOT require it as the canonical runtime root.

#### Scenario: Legacy runtime path exists
- **WHEN** `/int/.runtime` exists after migration
- **THEN** it is treated as compatibility routing to `/int/tools/.runtime`
- **AND** new intTools runtime writes target `/int/tools/.runtime` by default
