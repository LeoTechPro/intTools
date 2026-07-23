# Tilda MCP

Read/export MCP for all seven methods in the official Tilda API. It does not
edit or publish pages.

Both wrappers call `launcher.py`:

- Windows: `run-tilda-mcp.cmd`
- Linux: `run-tilda-mcp.sh`

The launcher reads only a protected env file. Default pointers:

- Windows: `%LOCALAPPDATA%\intdata\secrets\punkt-b\tilda.env`
- VDS: `/home/agents/.hermes/secrets/punkt-b/tilda/secrets.env`

Override only the pointer with `TILDA_SECRET_FILE`. The file must contain
`TILDA_PUBLIC_KEY`, `TILDA_SECRET_KEY` and optional `TILDA_PROJECT_ID`; on
POSIX it must be mode `0600` or stricter. Do not place keys in Codex/Hermes
configuration or repository files.
