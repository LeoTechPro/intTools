## ADDED Requirements

### Requirement: Codex hooks MUST inject managed contour context
The system MUST inject machine/repository contour context for managed intData backend checkouts before agents perform task work.

#### Scenario: Dev backend checkout session starts
- **WHEN** Codex starts or receives a prompt with cwd inside `agents@vds.intdata.pro:/int/data`
- **THEN** the hook context identifies the contour as `intdata-dev`
- **AND** the context states that backend edits and commits belong on `/int/data` `main`
- **AND** the agent is told not to rediscover dev/prod by hostname and path unless direct evidence conflicts.

#### Scenario: Prod backend checkout session starts
- **WHEN** Codex starts or receives a prompt with cwd inside `agents@vds.punkt-b.pro:/int/punkt-b`
- **THEN** the hook context identifies the contour as `punktb-prod`
- **AND** the context states that the checkout is read-only for agents and refreshes from `origin/main`.

#### Scenario: VDS intTools mirror session starts
- **WHEN** Codex starts or receives a prompt with cwd inside `/int/tools` on `agents@vds.intdata.pro` or `agents@vds.punkt-b.pro`
- **THEN** the hook context identifies the contour as `inttools-vds-mirror`
- **AND** the context states that tracked changes belong in `D:\int\tools`
- **AND** the VDS checkout is treated as a read-only mirror refreshed from `origin/main`.

### Requirement: Codex hooks MUST guard managed contour git mutations
The system MUST block unsafe mutating git commands when the current host/path/branch does not match the managed contour policy.

#### Scenario: Agent tries to commit on prod
- **WHEN** Codex attempts a Bash command containing `git commit` in `/int/punkt-b`
- **THEN** the hook denies the command
- **AND** the denial explains that changes must be made on `agents@vds.intdata.pro:/int/data`, published to `origin/main`, then refreshed on prod.

#### Scenario: Agent tries to mutate a managed repo on the wrong host
- **WHEN** Codex attempts a mutating git command in a managed checkout on a host that does not match the contour
- **THEN** the hook denies the command before execution.

#### Scenario: Agent tries to edit intTools tracked files on VDS
- **WHEN** Codex attempts a mutating git command in `/int/tools` on either VDS
- **THEN** the hook denies the command
- **AND** the denial explains the required flow: `D:\int\tools` -> `origin/main` -> VDS refresh.

### Requirement: Codex hook source MUST stay repo-owned
The system MUST keep hook business logic in `/int/tools/codex/hooks` rather than embedding it in Codex home.

#### Scenario: Host hooks are installed
- **WHEN** Codex home hooks are configured on a VDS
- **THEN** `~/.codex/hooks.json` only points to the repo-owned dispatcher
- **AND** runtime hook logs are written under `/int/tools/.runtime/**`.
