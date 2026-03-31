# lockctl MCP adapter (OpenClaw)

Единый MCP server для `lockctl` запускается через:

- Linux: `/int/tools/openclaw/bin/mcp-lockctl.sh`
- Windows: `D:\int\tools\openclaw\bin\mcp-lockctl.cmd`

Оба adapter-скрипта делегируют в канонический Codex launcher:

- `/int/tools/codex/bin/mcp-lockctl.py`

Доступные typed tools:

- `lockctl_acquire`
- `lockctl_renew`
- `lockctl_release_path`
- `lockctl_release_issue`
- `lockctl_status`
- `lockctl_gc`

Runtime state общий для Codex/OpenClaw в рамках одного хоста и определяется `lockctl_core`.

Adapter-manifest для OpenClaw:

- `D:\int\tools\openclaw\.mcp.json` (Windows)
- `/int/tools/openclaw/.mcp.json` (Linux)
