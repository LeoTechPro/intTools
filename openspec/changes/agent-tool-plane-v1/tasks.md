## 1. Spec

- [x] 1.1 Add proposal, tasks, and process spec delta for `INT-226`.
- [x] 1.2 Record the sync-gate start override as an owner-approved exception.

## 2. Implementation

- [x] 2.1 Add capability skills for intdata-control, intdata-runtime, intbrain, and intdb.
- [x] 2.2 Update root plugin skills to route agents to the capability skills.
- [x] 2.3 Add plugin discovery metadata for local Codex app surfacing.
- [x] 2.4 Add IntBrain write/import mutation guards.
- [x] 2.5 Add remote ChatGPT tool-only MCP app v1 design documentation.
- [x] 2.6 Add verifier script for manifests, MCP smoke, skill coverage, and guard checks.

## 3. Validation

- [x] 3.1 Run JSON manifest validation.
- [x] 3.2 Run MCP `initialize`, `ping`, and `tools/list` smoke for all profiles.
- [x] 3.3 Run capability skill coverage validation.
- [x] 3.4 Run mutation guard-negative validation.
- [x] 3.5 Run OpenSpec strict validation and routing validation.
- [x] 3.6 Run selected live checks that are safe in the current environment.

## Exceptions

- Owner approved bypassing `sync_gate start` for `INT-226` because the checkout already had unrelated dirty/ahead work. This change must not touch those unrelated files.
