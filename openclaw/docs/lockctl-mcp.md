# lockctl MCP adapter (OpenClaw)

Единый MCP server для `lockctl` запускается через shared `intdata-control` runtime:

- Linux: `/int/tools/codex/bin/mcp-intdata-cli.sh --profile intdata-control`
- Windows: `D:\int\tools\codex\bin\mcp-intdata-cli.cmd --profile intdata-control`

Фактическая реализация:

- `/int/tools/lockctl/lockctl_core.py` для lock engine
- `/int/tools/codex/bin/mcp-intdata-cli.py --profile intdata-control` для MCP surface

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
