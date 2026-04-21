## ADDED Requirements

### Requirement: Routing registry MUST resolve logical intents through machine-readable bindings
The system MUST define a machine-readable routing registry for agent runtime-critical capabilities instead of using shell-specific wrapper paths as the source-of-truth.

#### Scenario: Known intent is resolved
- **WHEN** an agent receives a known high-risk intent for `/int/*`
- **THEN** the registry resolves that intent through `logical_intents[]` and `runtime_bindings`
- **AND** the routing result is one of `primary`, `fallback`, `blocked`, or `ambiguous`

### Requirement: High-risk bindings MUST declare engine and adapter metadata
The system MUST declare binding metadata for each high-risk capability so the resolver can distinguish canonical engines from platform adapters and enforce parity.

#### Scenario: High-risk capability is registered
- **WHEN** a binding is added for a high-risk capability
- **THEN** it includes `binding_kind`, `binding_origin`, `platforms_supported`, `adapter_targets_engine`, and `parity_required`
- **AND** `parity_required` is `true` for high-risk bindings

### Requirement: Runtime-critical capabilities MUST use one canonical engine and thin adapters
The system MUST assign exactly one canonical engine to each runtime-critical capability and MUST restrict shell-specific entrypoints to thin adapters without business logic.

#### Scenario: Capability is executed on Windows or Linux
- **WHEN** a runtime-critical capability is launched from either platform
- **THEN** the adapter forwards to the same canonical engine contract
- **AND** the adapter preserves the same CLI surface and exit semantics rather than acting as an independent implementation path

### Requirement: Missing engine, unsupported platform, or adapter drift MUST block execution
The system MUST block routing if the current platform has no supported binding, if the canonical engine is missing, or if an adapter no longer matches the engine contract.

#### Scenario: Binding cannot satisfy the contract
- **WHEN** a binding lacks a supported platform, lacks its target engine, or drifts from the canonical engine contract
- **THEN** routing returns `blocked`
- **AND** the agent does not improvise a new path outside the registry

### Requirement: Remote access routing MUST resolve through one shared SSH resolver engine
The system MUST route remote access capabilities through one shared canonical SSH resolver engine and MUST return the same metadata contract on Windows and Linux.

#### Scenario: SSH target is resolved
- **WHEN** the agent resolves remote access for a managed host
- **THEN** the engine returns `destination`, `transport`, `probe_succeeded`, `fallback_used`, `tailnet_host`, and `public_host`
- **AND** platform adapters do not change the metadata shape

### Requirement: Browser runtime launchers MUST be platform-neutral at the capability level
The system MUST route Firefox MCP launcher capabilities through a platform-neutral engine and MUST keep project overlays free of Windows-only launcher hardcodes where Linux execution is supported.

#### Scenario: Project overlay launches Firefox MCP runtime
- **WHEN** a project overlay or template binds a Firefox MCP launcher
- **THEN** it points to a platform-appropriate adapter for the same canonical launcher capability
- **AND** it does not hardcode `cmd.exe` plus a Windows-only absolute path as the only supported runtime binding

### Requirement: DB diagnostics, lock/sync, and host runtime launchers MUST participate in V1 inventory
The system MUST include repo-owned DB diagnostics, lock/sync, and host runtime launcher capabilities in the V1 routing inventory.

#### Scenario: V1 inventory is defined
- **WHEN** the registry and capability spec enumerate runtime-critical tooling
- **THEN** they include `intdb`, `lockctl`, `lockctl-mcp` through `mcp-intdata-cli --profile intdata-control`, `codex-host-bootstrap`, `codex-host-verify`, and `codex-recovery-bundle`
- **AND** those capabilities inherit the same engine/adapter and blocker rules as the rest of V1 high-risk scope

### Requirement: Verified skill fallbacks MUST be explicit
The system MUST allow `binding_origin = verified_skill` only as an explicit approved fallback and MUST keep repo-owned capabilities as the default source-of-truth for V1 high-risk intents.

#### Scenario: Verified skill binding is present
- **WHEN** a verified skill tool is registered for a high-risk path
- **THEN** it appears as an explicit fallback binding with `binding_origin = verified_skill`
- **AND** it does not replace the repo-owned primary binding implicitly
