# bitrix24-mcp

Read-only MCP server for Bitrix24 REST webhooks.

This server is separate from the official Bitrix24 remote MCP. It exists for
REST webhook reads that the official MCP does not expose, especially CRM deal
and contact inspection.

## Configuration

Use a local `.env` file next to this README or process environment:

```env
BITRIX_WEBHOOK_URL=https://example.bitrix24.ru/rest/1/webhook-code/
```

`BITRIX_WEBHOOK_BASE_URL` is also accepted.

Do not commit real webhook URLs.

## Smoke checks

```powershell
python -m bitrix24_mcp --check
python -m bitrix24_mcp --profile-smoke
```

## Tools

- `bitrix24_health` - safe configuration status.
- `bitrix24_profile` - current webhook user profile.
- `bitrix24_deal_fields` / `bitrix24_deal_get` / `bitrix24_deal_list`.
- `bitrix24_contact_fields` / `bitrix24_contact_get` / `bitrix24_contact_list`.
- `bitrix24_company_get` / `bitrix24_company_list`.
- `bitrix24_lead_get` / `bitrix24_lead_list`.
- `bitrix24_activity_list` - read CRM activities.
- `bitrix24_timeline_comment_list` - read timeline comments.
- `bitrix24_status_list` - read CRM status dictionaries.
- `bitrix24_raw_read_call` - generic allowlisted read-only REST call.

Mutating REST verbs are intentionally blocked.
