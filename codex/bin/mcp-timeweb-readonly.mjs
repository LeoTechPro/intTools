#!/usr/bin/env node
import { Server } from "../tools/mcp-obsidian-memory/node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js";
import { StdioServerTransport } from "../tools/mcp-obsidian-memory/node_modules/@modelcontextprotocol/sdk/dist/esm/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "../tools/mcp-obsidian-memory/node_modules/@modelcontextprotocol/sdk/dist/esm/types.js";

const API_BASE_URL = process.env.TIMEWEB_API_BASE_URL || "https://api.timeweb.cloud/api/v1";
const TIMEWEB_TOKEN = process.env.TIMEWEB_TOKEN || "";

if (!TIMEWEB_TOKEN) {
  process.stderr.write("TIMEWEB_TOKEN is not set.\n");
  process.exit(1);
}

const toolDefinitions = [
  {
    name: "list_apps",
    description: "Read-only: список приложений Timeweb App Platform.",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "get_app",
    description: "Read-only: детали приложения Timeweb по app_id.",
    inputSchema: {
      type: "object",
      properties: {
        app_id: { type: "string", description: "ID приложения Timeweb" }
      },
      required: ["app_id"]
    }
  },
  {
    name: "get_app_deploys",
    description: "Read-only: список деплоев приложения Timeweb по app_id.",
    inputSchema: {
      type: "object",
      properties: {
        app_id: { type: "string", description: "ID приложения Timeweb" }
      },
      required: ["app_id"]
    }
  },
  {
    name: "get_app_logs",
    description: "Read-only: runtime/access logs приложения Timeweb по app_id.",
    inputSchema: {
      type: "object",
      properties: {
        app_id: { type: "string", description: "ID приложения Timeweb" },
        limit: { type: "integer", description: "Количество записей, по умолчанию 50" }
      },
      required: ["app_id"]
    }
  }
];

function makeResponse(payload) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2)
      }
    ]
  };
}

function assertString(value, fieldName) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${fieldName} is required`);
  }
  return value.trim();
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${TIMEWEB_TOKEN}`
    },
    signal: AbortSignal.timeout(30_000)
  });

  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }

  if (!response.ok) {
    const detail = typeof body === "string" ? body : JSON.stringify(body);
    throw new Error(`Timeweb API ${response.status}: ${detail}`);
  }

  return body;
}

const server = new Server(
  {
    name: "timeweb-readonly",
    version: "1.0.0"
  },
  {
    capabilities: {
      tools: {}
    }
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: toolDefinitions };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const name = request.params.name;
    const args = request.params.arguments || {};

    if (name === "list_apps") {
      const body = await apiGet("/apps");
      return makeResponse({
        count: Array.isArray(body?.apps) ? body.apps.length : 0,
        apps: body?.apps || []
      });
    }

    if (name === "get_app") {
      const appId = assertString(args.app_id, "app_id");
      const body = await apiGet(`/apps/${encodeURIComponent(appId)}`);
      return makeResponse(body?.app || body);
    }

    if (name === "get_app_deploys") {
      const appId = assertString(args.app_id, "app_id");
      const body = await apiGet(`/apps/${encodeURIComponent(appId)}/deploys`);
      return makeResponse({
        count: Array.isArray(body?.deploys) ? body.deploys.length : 0,
        deploys: body?.deploys || []
      });
    }

    if (name === "get_app_logs") {
      const appId = assertString(args.app_id, "app_id");
      const parsedLimit = Number(args.limit);
      const limit = Number.isFinite(parsedLimit) ? Math.max(1, Math.min(500, parsedLimit)) : 50;
      const body = await apiGet(`/apps/${encodeURIComponent(appId)}/logs?limit=${limit}`);
      return makeResponse(body);
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    return makeResponse({
      error: error instanceof Error ? error.message : String(error)
    });
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
