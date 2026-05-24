# Tilda MCP

Minimal read/export MCP server for the official Tilda API.

Secrets are expected from environment variables:

- `TILDA_PUBLIC_KEY`
- `TILDA_SECRET_KEY`
- `TILDA_PROJECT_ID` optional default project id

The server intentionally does not implement the Tilda webhook. Webhook handling
belongs to an always-on HTTP service because Tilda calls it after Publish.