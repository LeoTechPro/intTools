## ADDED Requirements

### Requirement: Neutral agent plane MUST treat facades as equal clients

`int-agent-plane` MUST expose a facade-neutral tool-call interface for `agno`, `openclaw`, and `codex_app`. The service MUST NOT require one facade to call through another facade.

#### Scenario: Facade calls a canonical tool
- **WHEN** a request is submitted to `POST /v1/tools/call`
- **THEN** the request includes `request_id`, `facade`, `principal`, `tool`, `args`, `context`, `dry_run`, and optional `approval_ref`
- **AND** `facade` is one of `agno`, `openclaw`, or `codex_app`
- **AND** the response includes `ok`, `result`, `policy_decision_id`, `tool_call_id`, and `error`

### Requirement: Agent plane MUST expose a minimal HTTP API

The service MUST bind to localhost by default and expose only the MVP HTTP API needed for health, discovery, dispatch, and audit inspection.

#### Scenario: Client discovers and calls tools
- **WHEN** a client calls `GET /health`
- **THEN** the service returns an OK health payload
- **WHEN** a client calls `GET /v1/tools`
- **THEN** the service lists canonical tools available through existing MCP profiles
- **WHEN** a client calls `GET /v1/audit/tool-calls`
- **THEN** the service returns recent sanitized audit entries

### Requirement: Agent plane MUST preserve canonical tool ownership

The service MUST dispatch to existing intData MCP profiles and canonical engines. It MUST NOT become the source of truth for memory, issues, specs, locks, jobs, or runtime host capabilities.

#### Scenario: Tool dispatch occurs
- **WHEN** a request passes validation and policy checks
- **THEN** the dispatcher calls the existing MCP runtime for the tool's canonical profile
- **AND** the service records audit metadata
- **AND** canonical memory/content remains in IntBrain
- **AND** canonical issue/spec/lock state remains in Multica, OpenSpec, and lockctl

### Requirement: Agent plane MUST reject out-of-scope Cabinet surfaces

Cabinet absorption is owned by `INT-225` outside this change. This change MUST NOT add Cabinet public tools, aliases, compatibility APIs, product shells, or `/int/brain` changes.

#### Scenario: Cabinet tool is requested
- **WHEN** a tool name starts with `cabinet_`, starts with `cabinet.`, contains `_cabinet_`, or ends with `_cabinet`
- **THEN** validation or policy rejects the request
- **AND** the tool is not included in neutral plane discovery

#### Scenario: IntBrain plugin is discovered in Codex App
- **WHEN** the active `intbrain` MCP profile is initialized and `tools/list` is called
- **THEN** the profile exposes `27` tools
- **AND** no active tool name contains `cabinet`
- **AND** active plugin metadata and active skills do not advertise Cabinet workflows

### Requirement: Guarded calls MUST require approval

Mutating, destructive, runtime-sensitive, or high-risk calls MUST be rejected unless the request carries explicit approval metadata.

#### Scenario: Guarded call lacks approval
- **WHEN** a request targets a guarded tool such as lock acquisition, OpenSpec mutation, publish, sync gate, host bootstrap, recovery bundle, browser launch, or IntBrain write/import
- **AND** `approval_ref` is absent
- **THEN** the service rejects the call with `policy_rejected`
- **AND** writes a sanitized audit entry with `source_facade`

### Requirement: Agent plane MUST provide repo-owned client surfaces

The repository MUST provide minimal client surfaces for Codex App, OpenClaw, and Agno/local usage without changing production Telegram or VDS runtime configuration by default.

#### Scenario: Facade clients are smoke-tested locally
- **WHEN** the Codex MCP client initializes
- **THEN** it exposes `agent_plane_tools`, `agent_plane_call`, and `agent_plane_audit_recent`
- **WHEN** OpenClaw uses its wrapper
- **THEN** it calls the localhost HTTP endpoint
- **WHEN** Agno/local harness runs
- **THEN** it calls the same localhost HTTP endpoint

### Requirement: int-tools plugin guidance MUST be actionable for Codex App

The repository MUST provide Russian-facing plugin metadata and capability skills for `intbrain`, `intdata-control`, `intdata-runtime`, and `intdb`. Each active MCP tool MUST have exactly one canonical tool-card inside its assigned capability skill.

#### Scenario: Skill guidance is verified
- **WHEN** `scripts/codex/verify_int_tools_plugins.py --report-json` runs
- **THEN** the report includes a `profile/tool -> skill -> missing_guidance` matrix
- **AND** every active tool-card includes `Когда`, `Required inputs`, `Optional/schema inputs`, `Режим`, `Approval / issue requirements`, `Не использовать когда`, `Пример вызова`, and `Fallback/blocker`
- **AND** every required argument from the MCP schema is listed in the tool-card
- **AND** guarded or mutating tools mention owner approval, `confirm_mutation`, and `issue_context`
- **AND** read-only tools are explicitly marked read-only
- **AND** the active MCP counts are `intbrain=27`, `intdata-control=35`, `intdata-runtime=9`, and `intdb=1`
