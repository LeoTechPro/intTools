## ADDED Requirements

### Requirement: intTools MUST use repo-local Codex hooks for contour guardrails

The system MUST keep `/int/tools` Codex hook behavior in tracked repo-local `.codex/**` files.

#### Scenario: Agent starts in a VDS intTools mirror
- **WHEN** Codex starts or receives a prompt in `/int/tools` on a VDS host
- **THEN** the hook injects read-only mirror context
- **AND** tracked-file edits, dependency installs, commits and pushes are blocked
- **AND** safe reads plus `git fetch` and `git pull` remain allowed

#### Scenario: Agent starts in the Windows intTools source checkout
- **WHEN** Codex starts or receives a prompt in `D:\int\tools`
- **THEN** the hook injects source-checkout context
- **AND** normal source edits are not blocked by the hook
- **AND** push, OpenSpec mutations and secret staging require explicit approval markers
