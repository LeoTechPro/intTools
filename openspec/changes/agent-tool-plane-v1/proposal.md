# Change: Neutral Agent Tool Plane V1

## Why

Agno, OpenClaw, and Codex App need to call intData tools as equal clients instead of routing through each other. The shared layer must normalize requests, apply policy, dispatch to existing canonical MCP profiles, and keep audit/runtime state without becoming a new source of truth for memory, issues, specs, locks, or jobs.

## What Changes

- Add `int-agent-plane`, a localhost-only neutral Tool/Policy/State Plane service for `agents@vds.intdata.pro`.
- Expose HTTP endpoints for health, tool discovery, tool calls, and recent audit entries.
- Add a facade-neutral request envelope for `agno`, `openclaw`, and `codex_app`.
- Add policy gates that reject unknown facades/principals, Cabinet tools, and guarded mutations without explicit approval.
- Add an audit/state schema `agent_plane` for PostgreSQL, with JSONL fallback for local development.
- Add minimal clients for Codex App MCP, OpenClaw shell wrapper, and Agno/local harness.
- Fix the `ssh_resolve` preflight mismatch by using canonical capability `int_ssh_resolve`.
- Harden int-tools plugin guidance for Codex App: Russian plugin metadata, Russian capability skills, and a required tool-card for every active MCP tool.
- Exclude Cabinet from the active IntBrain tool surface; the active IntBrain MCP count becomes `27`.

## Scope Boundaries

- Cabinet absorption is owned by `INT-225` outside this change.
- This change MUST NOT add `cabinet_*` public tools, aliases, compatibility APIs, product shells, or `/int/brain` changes.
- Cabinet MUST NOT appear in active plugin metadata, active skills, or MCP `tools/list`.
- Canonical memory/context remains in IntBrain; `agent_plane.memory_refs` stores provenance references only.
- Canonical issue/spec/lock/runtime engines remain existing MCP profiles and CLI engines.
- PostgreSQL migration is delivered but not applied automatically.
- Runtime secrets stay outside git.
- Push, deploy, systemd install, and live VDS DB apply require separate owner approval.

## Issue

Owning Multica issue: `INT-226`.

## Acceptance

- OpenSpec for `agent-tool-plane-v1` validates strictly and describes neutral plane behavior.
- HTTP service exposes `GET /health`, `GET /v1/tools`, `POST /v1/tools/call`, and `GET /v1/audit/tool-calls`.
- `GET /v1/tools` excludes Cabinet tools.
- Guarded/mutating calls without `approval_ref` are rejected and audited.
- Codex MCP client lists and calls the neutral plane surface.
- Agno/local harness and OpenClaw wrapper can call the localhost service without changing Telegram/runtime config.
- Routing validation passes and fresh `ssh_resolve` uses `int_ssh_resolve`.
- Plugin manifests and skills are Russian-facing where possible while technical tool names and schema fields remain stable.
- Active MCP counts are `intbrain=27`, `intdata-control=35`, `intdata-runtime=9`, and `intdb=1`.
- `scripts/codex/verify_int_tools_plugins.py --report-json` reports `ok=true` with zero missing guidance.
