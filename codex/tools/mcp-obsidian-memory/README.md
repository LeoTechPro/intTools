# mcp-obsidian-memory

Локальный MCP сервер для vault `/2brain`.

Сервер работает с root-vault `2brain`; индекс OpenClaw при этом может использовать более узкий include-набор директорий, чтобы не тащить архивный и служебный шум в memory search.

## Tools
- `vault_status`
- `list_notes`
- `read_note`
- `search_notes`
- `upsert_note`
- `move_note_para`
- `link_notes`
- `audit_links`
- `suggest_links`

## Run

```bash
cd /int/tools/codex/tools/mcp-obsidian-memory
npm start
```

## Smoke

```bash
/home/leon/.nvm/versions/node/v24.8.0/bin/node \
  /int/tools/codex/tools/mcp-obsidian-memory/scripts/smoke-client.mjs
```
