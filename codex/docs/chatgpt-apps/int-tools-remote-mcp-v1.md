# int-tools remote MCP app v1

## Purpose

Expose a curated, internal, tool-only ChatGPT Apps/Connectors surface for intData agent tooling. The remote app is not a mirror of every local Codex plugin tool. It is a small HTTPS MCP endpoint that selects safe capabilities from IntBrain and intData Control.

## Sources

- OpenAI Apps SDK docs: `https://developers.openai.com/apps-sdk/`
- OpenAI MCP guide: `https://developers.openai.com/api/docs/mcp`

## V1 shape

- Archetype: tool-only remote MCP app.
- Endpoint: stable HTTPS `/mcp`.
- Auth: bearer/service token from runtime secret store.
- UI: none in v1.
- Logging: request id, actor, tool name, latency, result class, and guard decision.
- Secrets: never tracked in git.

## Curated tools

### Knowledge/read layer

- `search`: search IntBrain context/memory by owner-scoped query.
- `fetch`: fetch a specific context item, memory item, or provenance record.

These use standard connector-style names for knowledge retrieval and deep-research compatibility.

### Guarded action layer

Initial candidates:

- `openspec_status`: read-only status for an approved change.
- `openspec_show`: read-only spec/change fetch.
- `routing_validate`: read-only high-risk routing registry validation.
- `lockctl_status`: read-only lock inspection.

Do not expose publish, sync-gate finish, Multica operations, daemon control, DB apply, browser launch, or vault non-dry-run in v1. Multica remains available through the official `multica` CLI or official Multica MCP plugin when installed, not through this intData Control surface.

## Annotations

- Read tools use `readOnlyHint=true`.
- Mutating tools are out of v1 unless separately approved.
- Any future mutating tool must use `destructiveHint` accurately, require explicit issue context, and write an audit event.

## Local development check

1. Start the remote MCP server locally.
2. Expose it with a temporary HTTPS tunnel.
3. Register the app in ChatGPT Developer Mode using the tunnel `/mcp` URL.
4. Verify `search`, `fetch`, and one read-only control action.
5. Replace the tunnel with stable HTTPS hosting before production use.

## Production gate

Production enablement requires:

- stable HTTPS endpoint;
- secret-store backed auth;
- rate limits and request logging;
- operator runbook;
- smoke tests for `search`, `fetch`, auth failure, and one read-only control action.
