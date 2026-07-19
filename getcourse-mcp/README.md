# GetCourse MCP

Agent-agnostic MCP server for the public API documented at
[`getcourse.ru/help/api`](https://getcourse.ru/help/api). A committed manifest
tracks the complete documented Import/Export surface and its MCP coverage.
Read-only tools are the default surface. Write tools are limited to documented
Import API endpoints and require `confirm_write=True` on every call.

The server never stores secrets in tracked files. Put local credentials into `.env`
next to this README or provide them through the process environment.

## Configuration

Copy `.env.example` to `.env` and fill:

```env
GETCOURSE_ACCOUNT_DOMAIN=your-account.getcourse.ru
GETCOURSE_API_KEY=your-getcourse-api-key
```

Older punctb variable names are also accepted:

```env
GETCOURSE_LMS_PUNCTB_PRO_API_KEY=...
GETCOURSE_LMS_PUNKTB_PRO_API_KEY=...
```

## Smoke checks

Configuration-only check:

```powershell
python -m getcourse_mcp --check
```

Live read-only groups request:

```powershell
python -m getcourse_mcp --groups-smoke
```

## MCP entrypoint

For stdio transport on Windows:

```powershell
D:\int\tools\getcourse-mcp\run-getcourse-mcp.cmd
```

## Tools

- `getcourse_health` - shows whether domain and API key are configured.
- `getcourse_api_manifest` - returns official source and coverage metadata.
- `getcourse_groups_list` - lists GetCourse groups.
- `getcourse_fields_list` - reads user/deal additional-field directories through fixed `POST action=get`.
- `getcourse_start_export` - starts users, orders/deals, or payments export.
- `getcourse_export_get` - reads a completed export by id.
- `getcourse_export_wait` - polls an export with bounded attempts.
- `getcourse_group_users_export` - starts a filtered group users export.
- `getcourse_users_export_start` - starts a users export with typed filters.
- `getcourse_deals_export_start` - starts a deals export with typed filters.
- `getcourse_payments_export_start` - starts a payments export with typed filters.
- `getcourse_users_export_wait` - starts and polls a filtered users export.
- `getcourse_deals_export_wait` - starts and polls a filtered deals export.
- `getcourse_raw_get` - read-only GET limited to manifest account endpoints.
- `getcourse_user_import` - guarded `POST /pl/api/users action=add`.
- `getcourse_user_groups_update` - guarded `POST /pl/api/users action=update`.
- `getcourse_deal_import` - guarded `POST /pl/api/deals action=add`.
- `getcourse_deal_status_update` - guarded deal status update through `POST /pl/api/deals action=add`.

Typed export tools require at least one filter to avoid accidental full-account
or full-group exports from MCP. The generic start tool enforces the same rule.
User exports support the documented `email` and `idgrouplist` parameters, but
`idgrouplist` alone is not treated as an object filter. Polling tools clamp attempts to 1..10 and
interval to 0..10 seconds.

GetCourse documents Export API as single-threaded per account and limited to 100
export requests per 2 hours. Export errors `903` and observed `905` are returned
as transient throttle/busy responses with a retry hint.

Write tools are not smoke-tested live by default. They use GetCourse Import API,
which GetCourse documents for import/update flows rather than operational object
management.

Browser-only lesson playback, video access and account management are outside
the public API manifest and remain web UI workflows.
