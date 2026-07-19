# amoCRM MCP Server

Agent-agnostic MCP server for [amoCRM](https://www.amocrm.ru/) and Umnico. It keeps the existing typed CRM tools and adds manifest-backed access to the complete documented public amoCRM HTTP API surface.

Built with [FastMCP](https://github.com/jlowin/fastmcp). Works with Claude Desktop, Cursor, and any MCP-compatible client.

## Features

- **49 MCP tools**, including existing typed workflows and complete manifest-backed API access
- **236 documented endpoints** across REST/Webhooks, Chats, Files and telephony
- **Reproducible parity manifest** generated only from official amoCRM documentation
- **Chats HMAC-SHA1** request signing and **Files API binary/base64** transport
- **OAuth 2.0** token refresh with disk persistence
- **Rate limiting** — 7 req/s with automatic 429 backoff and jitter
- **HAL+JSON normalization** — strips `_links`, flattens `_embedded`
- **Consistent response envelopes** — `{data, pagination}` or `{error, status_code, detail}`
- **stdio and SSE** transports

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your amoCRM credentials:

```bash
cp .env.example .env
```

You need at minimum:
- `AMO_SUBDOMAIN` — your amoCRM account subdomain
- `AMO_ACCESS_TOKEN` — OAuth access token

For automatic token refresh, also set:
- `AMO_CLIENT_ID`, `AMO_CLIENT_SECRET`, `AMO_REFRESH_TOKEN`

For Chats API set `AMO_CHAT_SECRET` in the host's native secret store. Files API discovers `drive_url` from the account; `AMO_DRIVE_URL` is an optional explicit override. Never commit real values.

### 3. Run

```bash
# stdio (default — for Claude Desktop, Cursor, etc.)
python -m amocrm_mcp

# SSE transport
AMO_TRANSPORT=sse AMO_PORT=8000 python -m amocrm_mcp
```

### Claude Desktop config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "amocrm": {
      "command": "python",
      "args": ["-m", "amocrm_mcp"],
      "env": {
        "AMO_SUBDOMAIN": "your-subdomain",
        "AMO_ACCESS_TOKEN": "your-token"
      }
    }
  }
}
```

## Tools

| Domain | Tools | Description |
|--------|-------|-------------|
| **Leads** | `leads_list`, `leads_get`, `leads_search`, `leads_create`, `leads_create_complex`, `leads_update` | Full lead lifecycle |
| **Contacts** | `contacts_get`, `contacts_search`, `contacts_create`, `contacts_update` | Contact management |
| **Companies** | `companies_get`, `companies_search`, `companies_create`, `companies_update` | Company management |
| **Tasks** | `tasks_list`, `tasks_get`, `tasks_create`, `tasks_update` | CRM task operations |
| **Notes** | `notes_list`, `notes_create` | Notes on entities |
| **Pipelines** | `pipelines_list`, `pipelines_get`, `pipelines_list_statuses` | Pipeline & status info |
| **Associations** | `associations_get_linked`, `associations_link_entities` | Entity relationships |
| **Account** | `account_get`, `account_list_users`, `account_list_custom_fields` | Account metadata |
| **Batch** | `batch_create_leads`, `batch_create_contacts`, `batch_update_leads` | Bulk operations |
| **Analytics** | `analytics_get_events`, `analytics_get_pipeline_analytics`, +1 | CRM analytics |
| **Unsorted** | `unsorted_list`, `unsorted_accept`, `unsorted_reject` | Unsorted inbox |
| **Complete API** | `amocrm_api_manifest`, `amocrm_api_endpoints`, `amocrm_api_call` | Every endpoint in the committed official registry |

`amocrm_api_call` deliberately has no connector-specific confirmation flag. Codex, Hermes, or another MCP host remains responsible for its own write/destructive-action policy.

## API parity audit

Regenerate the endpoint manifest from official documentation and run tests:

```powershell
python scripts/update_api_manifest.py
python -m pytest -q
```

The browser-only `APP.notifications` JavaScript API is explicitly recorded as excluded because it is not a server HTTP API.

## Getting amoCRM Credentials

1. Go to your amoCRM account → **Settings** → **Integrations**
2. Create a new integration (or use an existing one)
3. Copy the **access token**, **client ID**, and **client secret**
4. Your subdomain is the part before `.amocrm.ru` in your account URL

## License

MIT
