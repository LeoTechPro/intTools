## ADDED Requirements

### Requirement: IntBrain MUST be the only repo-owned memory surface
The system MUST expose repo-owned agent memory/context operations through the `intbrain` plugin/profile only.

#### Scenario: Agent memory tools are listed
- **WHEN** IntData Tools plugin catalog and MCP profiles are inspected
- **THEN** `intbrain` is the only repo-owned memory/context plugin surface
- **AND** no active `intmemory`, `mcp-intmemory`, or `mempalace` plugin/tool entry remains

### Requirement: Session memory import MUST preserve traceability and redaction
The system MUST preserve session source traceability, deduplication, and secret redaction when moving `intmemory` behavior into `intbrain`.

#### Scenario: Codex session memory is imported
- **WHEN** an in-scope Codex or OpenClaw session JSONL file is imported
- **THEN** stored IntBrain context items include source, source_path, source_hash, chunk_kind, and tags
- **AND** token-like values are redacted before storage
- **AND** duplicate source_hash values are skipped

### Requirement: MemPalace removal MUST be count-checked before runtime deletion
The system MUST inventory MemPalace runtime data before deleting machine-local MemPalace runtime paths.

#### Scenario: MemPalace runtime cleanup is requested
- **WHEN** MemPalace repo/runtime data exists on local PC or VDS
- **THEN** the migration/import path reports candidate counts first
- **AND** runtime deletion proceeds only after the count-check is recorded for INT-222
- **AND** no compatibility alias is kept after cleanup

### Requirement: Cabinet MUST be absorbed into IntBrain before active plugin removal
The system MUST provide an IntBrain-owned Cabinet inventory/import path before removing Cabinet from the active intTools plugin catalog.

#### Scenario: Cabinet plugin surface is removed
- **WHEN** the active intTools plugin catalog is inspected after the cutover
- **THEN** `cabinet` is absent as an active plugin ID
- **AND** `intbrain` exposes Cabinet inventory/import capability
- **AND** Cabinet workspace/runtime candidates are traceable with source names `intbrain.cabinet.workspace.v1` and `intbrain.cabinet.runtime.v1`
- **AND** physical deletion of `D:/int/cabinet` remains blocked until count-check and owner acceptance are recorded in INT-222

### Requirement: intData Control MUST be the only repo-owned control-plane plugin surface
The system MUST expose lockctl, Multica, OpenSpec, routing, sync gate, publish, gate, and commit-binding MCP tools through the `intdata-control` plugin/profile.

#### Scenario: Control-plane tools are listed
- **WHEN** the IntData Tools plugin catalog and MCP profiles are inspected
- **THEN** `intdata-control` is the only active control-plane plugin ID
- **AND** old plugin IDs `lockctl`, `multica`, `openspec`, and `intdata-governance` are absent from the active catalog
- **AND** public tool names remain the existing unique `lockctl_*`, `multica_*`, `openspec_*`, `routing_*`, `sync_gate`, `publish`, `gate_*`, and `commit_binding` names

### Requirement: Vault tools MUST be part of intData Runtime
The system MUST expose repo-owned vault sanitizer and runtime GC tools through `intdata-runtime`.

#### Scenario: Runtime tools are listed
- **WHEN** the `intdata-runtime` MCP profile is inspected
- **THEN** it includes `intdata_vault_sanitize` and `intdata_runtime_vault_gc`
- **AND** the old plugin ID `intdata-vault` is absent from the active catalog

### Requirement: Firefox profile launch MUST be registry-backed
The system MUST launch repo-owned Firefox MCP profiles through one launcher and a tracked profile registry.

#### Scenario: Browser profile launch is requested
- **WHEN** `browser_profile_launch` receives a supported profile key
- **THEN** the profile capability, profile key, start URL, and viewport are resolved from `codex/config/browser-profiles.v1.json`
- **AND** per-profile `mcp-firefox-assess-*` wrappers are not required as active bindings

### Requirement: Active intTools plugins MUST use Developer Tools category
The system MUST categorize active intTools plugins as developer/tooling surfaces rather than productivity surfaces.

#### Scenario: Plugin marketplace is inspected
- **WHEN** active intTools plugin metadata and marketplace entries are inspected
- **THEN** `intbrain`, `intdata-control`, `intdata-runtime`, and `intdb` use category `Developer Tools`
- **AND** removed plugin IDs have no active marketplace category
