# getcourse-mcp

Read-only MCP server for the GetCourse account API.

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

For stdio transport:

```powershell
D:\int\tools\codex\tools\getcourse-mcp\run-getcourse-mcp.cmd
```

## Tools

- `getcourse_health` - shows whether domain and API key are configured.
- `getcourse_groups_list` - lists GetCourse groups.
- `getcourse_start_export` - starts users, orders/deals, or payments export.
- `getcourse_export_get` - reads a completed export by id.
- `getcourse_group_users_export` - starts group users export.
- `getcourse_raw_get` - safe read-only GET under `/pl/api/account/...`.
