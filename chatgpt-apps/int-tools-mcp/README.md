# intData Tools ChatGPT MCP

Internal, tool-only ChatGPT Apps MCP server for a curated intData read-only tool surface.

## Local run

```powershell
cd D:\int\tools\chatgpt-apps\int-tools-mcp
python -m int_tools_mcp.server --host 127.0.0.1 --port 9193
```

Endpoint: `http://127.0.0.1:9193/mcp`

Set `INT_TOOLS_MCP_BEARER_TOKEN` for bearer-token auth. Set `INT_TOOLS_MCP_OWNER_ID` when callers should not pass `owner_id` to `search`.

## Tool surface

The v1 surface is intentionally small and read-only:

- `search`
- `fetch`
- `routing_validate`
- `lockctl_status`

It must not expose generic internal dispatch, OpenSpec tools, mutating lock tools, Multica operations, publish/sync wrappers, browser launch, DB apply, or vault non-dry-run.
