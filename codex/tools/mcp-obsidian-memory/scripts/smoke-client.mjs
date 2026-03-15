import { Client } from "../node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js";
import { StdioClientTransport } from "../node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js";

const client = new Client({ name: "obsidian-memory-smoke", version: "1.0.0" }, { capabilities: {} });
await client.connect(new StdioClientTransport({ command: "/git/tools/codex/bin/mcp-obsidian-memory.sh", args: [] }));

const tools = await client.listTools();
const status = await client.callTool({ name: "vault_status", arguments: {} });

console.log(JSON.stringify({
  tools: tools.tools.map((item) => item.name),
  vaultStatus: status.structuredContent
}, null, 2));

await client.close();
