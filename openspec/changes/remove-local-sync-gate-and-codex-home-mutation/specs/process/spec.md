## ADDED Requirements

### Requirement: Lockctl MUST remain a cross-platform writer-lock runtime
The system MUST keep `lockctl` as a repo-owned machine-local writer-lock runtime with one canonical core and consistent command semantics on Linux, macOS, and Windows.

#### Scenario: Lockctl CLI is used on supported platforms
- **WHEN** an operator or agent invokes `lockctl acquire`, `lockctl renew`, `lockctl release-path`, `lockctl release-issue`, `lockctl status`, or `lockctl gc`
- **THEN** the command is backed by `lockctl/lockctl_core.py`
- **AND** platform wrappers only adapt process launch mechanics
- **AND** command names and argument semantics remain consistent across Linux, macOS, and Windows

#### Scenario: Lockctl MCP is exposed
- **WHEN** an MCP runtime exposes lock tooling from this repo
- **THEN** it exposes `lockctl_*` tools through `codex/bin/mcp-intdata-cli.py --profile intdata-control`
- **AND** it does not require standalone `mcp-lockctl.*` wrappers

### Requirement: Repo git publication MUST use explicit native git commands
The system MUST NOT require repo-owned sync-gate wrappers for normal git synchronization, commit, or publication.

#### Scenario: Agent prepares or publishes repository changes
- **WHEN** a task needs git status, fetch, pull, commit, or push behavior
- **THEN** the agent uses explicit native git commands and repo hooks
- **AND** owner-approved `main` publication still requires `ALLOW_MAIN_PUSH=1`
- **AND** removed/forbidden `sync_gate_*` MCP tools and removed/forbidden `int_git_sync_gate` scripts are not required

### Requirement: Repo tooling MUST NOT manage Codex home internals
Repo-owned intTools scripts MUST NOT install, patch, mirror, generate, compare, delete, or enforce files under Codex home (`~/.codex` / `C:\Users\intData\.codex`).

#### Scenario: Host bootstrap runs
- **WHEN** host bootstrap is invoked
- **THEN** it may prepare repo-local runtime paths under `/int/tools/.runtime/**`
- **AND** it does not write Codex home
- **AND** it does not sync tracked assets into Codex home

#### Scenario: Host verification runs
- **WHEN** host verification is invoked
- **THEN** it checks repo-owned entrypoints and repo-local runtime prerequisites
- **AND** it does not validate, compare, or enforce Codex home overlay contents

### Requirement: Hidden Multica report delivery sidecars MUST NOT be active
The system MUST NOT provide repo-owned sidecars that silently deliver Multica hygiene reports into issue comments or external outboxes.

#### Scenario: Multica hygiene context is needed
- **WHEN** an agent needs Multica hygiene information
- **THEN** it uses the official `multica` CLI or official Multica MCP reads and reports explicitly in the current task context
- **AND** it does not call a repo-owned sidecar with hardcoded autopilot/report delivery defaults

## MODIFIED Requirements

### Requirement: Governance docs MUST stay synchronized with OpenSpec source-of-truth
The system MUST keep repo governance docs synchronized with the canonical OpenSpec process spec and active change package whenever tooling governance changes.

#### Scenario: Tooling governance changes
- **WHEN** process rules for tracked tooling mutations are changed
- **THEN** the relevant `openspec/specs/**` and `openspec/changes/**` content is updated together with repo governance docs such as `AGENTS.md` and `README.md`
- **AND** those docs do not become an unsynchronized second source-of-truth
- **AND** active docs do not reference removed local wrappers such as `int_git_sync_gate`, `sync_gate_*`, standalone `mcp-lockctl.*`, or Multica autopilot sidecars as supported paths
