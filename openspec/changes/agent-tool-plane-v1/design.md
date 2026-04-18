# Design: Neutral Agent Tool Plane V1

## Boundary
`int-agent-plane` is a facade-neutral runtime service. It does not own canonical memory, tasks, locks, specs, or issue state. It normalizes requests, checks policy, dispatches to existing canonical tools, and records audit.

Cabinet is explicitly excluded. Cabinet absorption is owned by `INT-225` in `/int/brain`; this change must not add Cabinet tools, aliases, or runtime dependencies.

## Runtime
- Host: `agents@vds.intdata.pro`.
- Bind: `127.0.0.1:9192`.
- Runtime env: outside git, for example `/home/agents/.config/int-agent-plane/agent-plane.env`.
- Source package: `/int/tools/agent_plane`.
- Service: user systemd unit template shipped in repo, installed separately.

## Request Flow
1. A facade sends a request envelope to `POST /v1/tools/call`.
2. The service validates `facade`, `principal`, `tool`, and `args`.
3. The policy layer rejects unknown facades/principals and guarded mutating tools without approval.
4. The dispatcher maps the tool to an existing MCP profile and performs a JSON-RPC `tools/call`.
5. The audit store records request metadata, policy decision, status, and sanitized result/error.
6. The service returns a facade-neutral response.

## Storage
PostgreSQL schema `agent_plane` stores runtime state and audit:
- `principal_map`
- `facade_sessions`
- `messages`
- `tool_calls`
- `approvals`
- `policy_decisions`
- `memory_refs`

Canonical memory/content remains in IntBrain. `memory_refs` stores provenance links only.

## MVP Tool Surface
- IntBrain context/search/policy tools.
- Read-only Multica issue/worklog reads.
- `lockctl_status`.
- Guarded `lockctl_acquire` and `lockctl_release`.
- Guarded OpenSpec/routing/runtime tools.

Existing public tool names are preserved.
