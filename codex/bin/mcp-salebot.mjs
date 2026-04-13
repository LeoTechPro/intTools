#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Server } from "../tools/mcp-obsidian-memory/node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js";
import { StdioServerTransport } from "../tools/mcp-obsidian-memory/node_modules/@modelcontextprotocol/sdk/dist/esm/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "../tools/mcp-obsidian-memory/node_modules/@modelcontextprotocol/sdk/dist/esm/types.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const primaryEnvPath = path.resolve(process.env.CODEX_SECRETS_ROOT || "/int/.runtime/codex-secrets", "salebot-punkt-b.env");
const legacyEnvPath = path.resolve(process.env.HOME || "", ".codex/var/salebot-punkt-b.env");
const defaultEnvPath = fs.existsSync(primaryEnvPath) ? primaryEnvPath : legacyEnvPath;

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const content = fs.readFileSync(filePath, "utf8");
  for (const rawLine of content.split(/\r?\n/u)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }
    const key = line.slice(0, separatorIndex).trim();
    let value = line.slice(separatorIndex + 1).trim();
    if (
      (value.startsWith("\"") && value.endsWith("\"")) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

loadEnvFile(process.env.SALEBOT_ENV_FILE || defaultEnvPath);

const SALEBOT_API_KEY = (process.env.SALEBOT_API_KEY || "").trim();
const SALEBOT_BASE_URL = (process.env.SALEBOT_BASE_URL || "https://chatter.salebot.pro").replace(/\/+$/u, "");

if (!SALEBOT_API_KEY) {
  process.stderr.write("SALEBOT_API_KEY is not set.\n");
  process.exit(1);
}

const toolDefinitions = [
  {
    name: "connected_channels",
    description: "Получить список подключённых каналов Salebot проекта.",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "get_clients",
    description: "Получить список клиентов Salebot. Можно ограничить результат локально параметром limit.",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "integer", description: "Максимум клиентов в ответе после локальной обрезки." }
      }
    }
  },
  {
    name: "call_api",
    description: "Универсальный вызов Salebot API для read/write сценариев.",
    inputSchema: {
      type: "object",
      properties: {
        method: {
          type: "string",
          description: "HTTP method: GET или POST."
        },
        action: {
          type: "string",
          description: "API action после /api/<token>/, например get_clients."
        },
        query: {
          type: "object",
          description: "Query-параметры для GET/POST."
        },
        body: {
          type: "object",
          description: "JSON body для POST."
        }
      },
      required: ["action"]
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

function ensurePlainObject(value, fieldName) {
  if (value == null) {
    return {};
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${fieldName} must be an object`);
  }
  return value;
}

function toSearchParams(input) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (value == null) {
      continue;
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item != null) {
          params.append(key, String(item));
        }
      }
      continue;
    }
    if (typeof value === "object") {
      params.append(key, JSON.stringify(value));
      continue;
    }
    params.append(key, String(value));
  }
  return params;
}

async function apiCall({ method = "GET", action, query = {}, body = null }) {
  const normalizedMethod = String(method || "GET").trim().toUpperCase();
  const normalizedAction = String(action || "").trim().replace(/^\/+/u, "");

  if (!normalizedAction) {
    throw new Error("action is required");
  }
  if (!["GET", "POST"].includes(normalizedMethod)) {
    throw new Error("method must be GET or POST");
  }

  const url = new URL(`${SALEBOT_BASE_URL}/api/${SALEBOT_API_KEY}/${normalizedAction}`);
  const params = toSearchParams(ensurePlainObject(query, "query"));
  for (const [key, value] of params.entries()) {
    url.searchParams.append(key, value);
  }

  const init = {
    method: normalizedMethod,
    headers: {
      Accept: "application/json"
    },
    signal: AbortSignal.timeout(30_000)
  };

  if (normalizedMethod === "POST") {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(ensurePlainObject(body, "body"));
  }

  const response = await fetch(url, init);
  const text = await response.text();

  let parsed;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = text;
  }

  if (!response.ok) {
    const detail = typeof parsed === "string" ? parsed : JSON.stringify(parsed);
    throw new Error(`Salebot API ${response.status}: ${detail}`);
  }

  return parsed;
}

const server = new Server(
  {
    name: "salebot-punktb",
    version: "1.0.0"
  },
  {
    capabilities: {
      tools: {}
    }
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: toolDefinitions }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const name = request.params.name;
    const args = request.params.arguments || {};

    if (name === "connected_channels") {
      return makeResponse(await apiCall({ action: "connected_channels" }));
    }

    if (name === "get_clients") {
      const limitRaw = Number(args.limit);
      const limit = Number.isFinite(limitRaw) ? Math.max(1, Math.min(500, limitRaw)) : null;
      const payload = await apiCall({ action: "get_clients" });
      if (!limit || !Array.isArray(payload?.clients)) {
        return makeResponse(payload);
      }
      return makeResponse({
        ...payload,
        clients: payload.clients.slice(0, limit),
        returned_count: Math.min(limit, payload.clients.length),
        total_count: payload.clients.length
      });
    }

    if (name === "call_api") {
      const payload = await apiCall({
        method: args.method,
        action: args.action,
        query: args.query,
        body: args.body
      });
      return makeResponse(payload);
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
