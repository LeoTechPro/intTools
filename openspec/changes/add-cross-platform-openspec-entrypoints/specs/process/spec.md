## ADDED Requirements

### Requirement: OpenSpec CLI entrypoints MUST be tracked and cross-platform
The system MUST keep repo-managed OpenSpec entrypoints in git for Linux and Windows runtimes so the local OpenSpec CLI can be launched consistently from both platforms.

#### Scenario: OpenSpec CLI is invoked from Linux or Windows
- **WHEN** an operator or agent uses the repo-managed OpenSpec launcher from Linux or Windows
- **THEN** a tracked entrypoint exists for the target platform in `codex/bin/`
- **AND** that entrypoint forwards to the locally installed OpenSpec CLI or returns an explicit install error instead of relying on ad-hoc machine-local wrappers
