# Change: Russian localization for int-tools plugin descriptions

## Why

Catalog cards for active `int-tools` plugins currently use English descriptions, while owner-facing communication is Russian.

## What Changes

- Localize user-facing text fields in active plugin manifests to Russian:
  - root `description`
  - interface `shortDescription`
  - interface `longDescription`
- Keep technical identifiers and runtime behavior unchanged:
  - `name` (plugin IDs)
  - `displayName`
  - MCP tool names/contracts
  - launchers and profiles

## Scope

- Active plugin manifests in `codex/plugins/*/.codex-plugin/plugin.json`.
