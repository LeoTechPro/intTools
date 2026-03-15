#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const VAULT_ROOT = path.resolve(process.env.OBSIDIAN_VAULT_ROOT || "/2brain");
const PARA_CATEGORIES = new Set([
  "Projects",
  "Areas",
  "Resources",
  "Archives",
  "Inbox",
  "Daily",
  "00_Index",
  "Templates"
]);

const changedNotes = new Set();

function normalizeRelInput(input) {
  if (typeof input !== "string") {
    throw new Error("Path must be a string.");
  }
  const normalized = input.trim().replace(/\\/g, "/").replace(/^\/+/, "");
  if (!normalized) {
    throw new Error("Path cannot be empty.");
  }
  return normalized;
}

function ensureMarkdownPath(relPath) {
  return relPath.endsWith(".md") ? relPath : `${relPath}.md`;
}

function toWikiPath(relPath) {
  return relPath.replace(/\\/g, "/").replace(/\.md$/i, "");
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function resolveVaultPath(relPath) {
  const normalized = normalizeRelInput(relPath);
  const absPath = path.resolve(VAULT_ROOT, normalized);
  const rootPrefix = `${VAULT_ROOT}${path.sep}`;
  if (!(absPath === VAULT_ROOT || absPath.startsWith(rootPrefix))) {
    throw new Error(`Path escapes vault root: ${relPath}`);
  }
  return { absPath, relPath: normalized.replace(/\\/g, "/") };
}

async function ensureDirForFile(absFilePath) {
  await fs.mkdir(path.dirname(absFilePath), { recursive: true });
}

async function pathExists(absPath) {
  try {
    await fs.access(absPath);
    return true;
  } catch {
    return false;
  }
}

async function readText(absPath) {
  return fs.readFile(absPath, "utf8");
}

async function writeText(absPath, content) {
  await ensureDirForFile(absPath);
  await fs.writeFile(absPath, content, "utf8");
}

async function walkMarkdownFiles(baseDir) {
  const out = [];
  async function walk(currentDir) {
    let entries;
    try {
      entries = await fs.readdir(currentDir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isSymbolicLink()) {
        continue;
      }
      if (entry.isDirectory()) {
        await walk(fullPath);
        continue;
      }
      if (entry.isFile() && entry.name.endsWith(".md")) {
        out.push(fullPath);
      }
    }
  }
  await walk(baseDir);
  return out;
}

async function listAllNotes() {
  const files = await walkMarkdownFiles(VAULT_ROOT);
  return files
    .map((abs) => path.relative(VAULT_ROOT, abs).replace(/\\/g, "/"))
    .sort((a, b) => a.localeCompare(b));
}

function parseWikiLinks(content) {
  const links = [];
  const regex = /\[\[([^\]]+)\]\]/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    const raw = (match[1] || "").trim();
    if (!raw) {
      continue;
    }
    const main = raw.split("|")[0]?.trim() || "";
    if (!main) {
      continue;
    }
    const noHeading = main.split("#")[0]?.trim() || "";
    if (!noHeading) {
      continue;
    }
    links.push(toWikiPath(noHeading));
  }
  return Array.from(new Set(links));
}

async function buildLinkGraph() {
  const notes = await listAllNotes();
  const outLinks = new Map();
  const inCount = new Map();

  for (const note of notes) {
    inCount.set(toWikiPath(note), 0);
  }

  for (const note of notes) {
    const { absPath } = resolveVaultPath(note);
    let content = "";
    try {
      content = await readText(absPath);
    } catch {
      content = "";
    }
    const links = parseWikiLinks(content);
    outLinks.set(note, links);
    for (const link of links) {
      if (inCount.has(link)) {
        inCount.set(link, (inCount.get(link) || 0) + 1);
      }
    }
  }

  return { notes, outLinks, inCount };
}

function zettelWarningsFor(relPath, graph) {
  const wikiPath = toWikiPath(relPath);
  const out = graph.outLinks.get(relPath) || [];
  const inCount = graph.inCount.get(wikiPath) || 0;
  const warnings = [];

  if (out.length === 0) {
    warnings.push({ code: "missing_outgoing_link", path: relPath, message: "Note has no outgoing wiki-links." });
  }
  if (inCount === 0) {
    warnings.push({ code: "missing_incoming_link", path: relPath, message: "Note has no incoming wiki-links." });
  }

  return { warnings, linksOut: out, linksInCount: inCount };
}

function formatFrontmatter(meta) {
  if (!meta || typeof meta !== "object" || Array.isArray(meta)) {
    return "";
  }
  const lines = ["---"];
  for (const [key, value] of Object.entries(meta)) {
    if (!key.trim()) {
      continue;
    }
    if (Array.isArray(value)) {
      const arr = value.map((item) => String(item)).join(", ");
      lines.push(`${key}: [${arr}]`);
      continue;
    }
    if (typeof value === "object" && value !== null) {
      lines.push(`${key}: ${JSON.stringify(value)}`);
      continue;
    }
    lines.push(`${key}: ${String(value)}`);
  }
  lines.push("---", "");
  return `${lines.join("\n")}\n`;
}

function composeNoteContent(args, relPath) {
  const baseName = path.basename(relPath, ".md");
  const title = typeof args.title === "string" && args.title.trim() ? args.title.trim() : baseName;
  const body = typeof args.body === "string" ? args.body.trimEnd() : "";
  const frontmatter = formatFrontmatter(args.meta);
  return `${frontmatter}# ${title}\n\n${body}\n`;
}

function buildBacklinkCandidates(targetRel, allNotes) {
  const targetDir = path.dirname(targetRel).replace(/\\/g, "/");
  const targetCategory = targetRel.split("/")[0] || "";
  const candidates = [
    "00_Index/Home MOC.md",
    `00_Index/${targetCategory} MOC.md`,
    `${targetCategory}/MOC.md`,
    `${targetDir}/MOC.md`
  ];

  const categoryMocs = allNotes.filter((note) => {
    if (!note.startsWith(`${targetCategory}/`)) {
      return false;
    }
    return path.basename(note).toLowerCase().includes("moc");
  });

  for (const moc of categoryMocs) {
    candidates.push(moc);
  }

  return Array.from(new Set(candidates)).filter((note) => allNotes.includes(note));
}

function addWikiLinkIfMissing(content, targetWiki) {
  const direct = new RegExp(`\\[\\[${escapeRegex(targetWiki)}(?:[#|][^\\]]*)?\\]\\]`, "i");
  if (direct.test(content)) {
    return { content, changed: false };
  }
  const suffix = content.endsWith("\n") ? "" : "\n";
  const updated = `${content}${suffix}\n- [[${targetWiki}]]\n`;
  return { content: updated, changed: true };
}

async function applyAutoBacklink(targetRel, graph) {
  const z = zettelWarningsFor(targetRel, graph);
  if (z.linksInCount > 0) {
    return { applied: false, source: null };
  }

  const candidates = buildBacklinkCandidates(targetRel, graph.notes);
  const source = candidates[0] || null;
  if (!source) {
    return { applied: false, source: null };
  }

  const sourceAbs = resolveVaultPath(source).absPath;
  const sourceContent = await readText(sourceAbs);
  const targetWiki = toWikiPath(targetRel);
  const linked = addWikiLinkIfMissing(sourceContent, targetWiki);

  if (!linked.changed) {
    return { applied: false, source };
  }

  await writeText(sourceAbs, linked.content);
  changedNotes.add(source);
  return { applied: true, source };
}

function replaceWikiReferences(content, oldRel, newRel) {
  const oldWiki = toWikiPath(oldRel);
  const newWiki = toWikiPath(newRel);
  let out = content;

  const patterns = [
    [new RegExp(`\\[\\[${escapeRegex(oldWiki)}((?:#[^\\]|]+)?(?:\\|[^\\]]+)?)\\]\\]`, "g"), `[[${newWiki}$1]]`],
    [new RegExp(`\\[\\[${escapeRegex(oldRel)}((?:#[^\\]|]+)?(?:\\|[^\\]]+)?)\\]\\]`, "g"), `[[${newRel}$1]]`]
  ];

  for (const [regex, replacement] of patterns) {
    out = out.replace(regex, replacement);
  }

  return out;
}

function makeResponse(payload) {
  return {
    content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
    structuredContent: payload
  };
}

function makeErrorResponse(error) {
  return {
    isError: true,
    content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }]
  };
}

const toolDefinitions = [
  {
    name: "vault_status",
    description: "Show Obsidian vault status for /2brain.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false }
  },
  {
    name: "list_notes",
    description: "List markdown notes in vault.",
    inputSchema: {
      type: "object",
      properties: {
        prefix: { type: "string", description: "Optional relative prefix filter." },
        limit: { type: "number", minimum: 1, maximum: 2000 }
      },
      additionalProperties: false
    }
  },
  {
    name: "read_note",
    description: "Read one note by relative path.",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "Relative note path (with or without .md)." }
      },
      required: ["path"],
      additionalProperties: false
    }
  },
  {
    name: "search_notes",
    description: "Simple text search over all notes.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string" },
        limit: { type: "number", minimum: 1, maximum: 200 },
        caseSensitive: { type: "boolean" }
      },
      required: ["query"],
      additionalProperties: false
    }
  },
  {
    name: "upsert_note",
    description: "Create or update note with optional soft Zettelkasten checks.",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string" },
        title: { type: "string" },
        body: { type: "string" },
        meta: { type: "object", additionalProperties: true },
        enforceLinks: { type: "string", enum: ["warn"] },
        autoBacklink: { type: "boolean" }
      },
      required: ["path"],
      additionalProperties: false
    }
  },
  {
    name: "move_note_para",
    description: "Move note into PARA category and patch backlinks.",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string" },
        targetCategory: {
          type: "string",
          enum: ["Projects", "Areas", "Resources", "Archives", "Inbox", "Daily", "00_Index", "Templates"]
        },
        targetSubpath: { type: "string" }
      },
      required: ["path", "targetCategory"],
      additionalProperties: false
    }
  },
  {
    name: "link_notes",
    description: "Add link between two notes (optionally bidirectional).",
    inputSchema: {
      type: "object",
      properties: {
        from: { type: "string" },
        to: { type: "string" },
        mode: { type: "string", enum: ["bidirectional", "forward"] }
      },
      required: ["from", "to"],
      additionalProperties: false
    }
  },
  {
    name: "audit_links",
    description: "Audit notes for missing incoming/outgoing Zettelkasten links.",
    inputSchema: {
      type: "object",
      properties: {
        scope: { type: "string", enum: ["all", "changed"] }
      },
      additionalProperties: false
    }
  },
  {
    name: "suggest_links",
    description: "Suggest or apply backlinks from MOC notes.",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string" },
        apply: { type: "boolean" }
      },
      additionalProperties: false
    }
  }
];

const server = new Server(
  {
    name: "obsidian-memory",
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

    if (name === "vault_status") {
      const notes = await listAllNotes();
      const paraCounts = {};
      for (const category of PARA_CATEGORIES) {
        paraCounts[category] = notes.filter((note) => note.startsWith(`${category}/`)).length;
      }
      return makeResponse({
        vaultRoot: VAULT_ROOT,
        notesCount: notes.length,
        paraCounts,
        changedNotes: Array.from(changedNotes).sort((a, b) => a.localeCompare(b))
      });
    }

    if (name === "list_notes") {
      const prefix = typeof args.prefix === "string" ? normalizeRelInput(args.prefix) : "";
      const limit = Number.isFinite(args.limit) ? Math.max(1, Math.min(2000, Number(args.limit))) : 200;
      const notes = await listAllNotes();
      const filtered = prefix ? notes.filter((note) => note.startsWith(prefix)) : notes;
      return makeResponse({
        count: filtered.length,
        notes: filtered.slice(0, limit)
      });
    }

    if (name === "read_note") {
      const relPath = ensureMarkdownPath(normalizeRelInput(args.path));
      const absPath = resolveVaultPath(relPath).absPath;
      const content = await readText(absPath);
      return makeResponse({ path: relPath, content });
    }

    if (name === "search_notes") {
      const query = String(args.query || "").trim();
      if (!query) {
        throw new Error("query is required");
      }
      const caseSensitive = Boolean(args.caseSensitive);
      const limit = Number.isFinite(args.limit) ? Math.max(1, Math.min(200, Number(args.limit))) : 20;
      const notes = await listAllNotes();
      const needle = caseSensitive ? query : query.toLowerCase();
      const results = [];
      for (const relPath of notes) {
        if (results.length >= limit) {
          break;
        }
        const absPath = resolveVaultPath(relPath).absPath;
        const content = await readText(absPath);
        const lines = content.split("\n");
        for (let i = 0; i < lines.length; i += 1) {
          const line = lines[i] || "";
          const haystack = caseSensitive ? line : line.toLowerCase();
          if (haystack.includes(needle)) {
            results.push({ path: relPath, line: i + 1, snippet: line.trim().slice(0, 300) });
            break;
          }
        }
      }
      return makeResponse({ query, count: results.length, results });
    }

    if (name === "upsert_note") {
      const relPath = ensureMarkdownPath(normalizeRelInput(args.path));
      const absPath = resolveVaultPath(relPath).absPath;
      const existed = await pathExists(absPath);

      const shouldRewrite = !existed || args.title !== undefined || args.body !== undefined || args.meta !== undefined;
      if (shouldRewrite) {
        const content = composeNoteContent(args, relPath);
        await writeText(absPath, content);
        changedNotes.add(relPath);
      }

      let graph = await buildLinkGraph();
      let backlink = { applied: false, source: null };
      if (Boolean(args.autoBacklink)) {
        backlink = await applyAutoBacklink(relPath, graph);
        graph = await buildLinkGraph();
      }

      const z = zettelWarningsFor(relPath, graph);
      return makeResponse({
        status: existed ? "updated" : "created",
        path: relPath,
        warnings: z.warnings,
        linksOut: z.linksOut,
        linksInCount: z.linksInCount,
        autoBacklink: backlink
      });
    }

    if (name === "move_note_para") {
      const sourceRel = ensureMarkdownPath(normalizeRelInput(args.path));
      const targetCategory = String(args.targetCategory || "").trim();
      if (!PARA_CATEGORIES.has(targetCategory)) {
        throw new Error(`targetCategory must be one of: ${Array.from(PARA_CATEGORIES).join(", ")}`);
      }
      const sourceAbs = resolveVaultPath(sourceRel).absPath;
      const sourceExists = await pathExists(sourceAbs);
      if (!sourceExists) {
        throw new Error(`Source note not found: ${sourceRel}`);
      }

      const sourceBaseName = path.basename(sourceRel);
      const targetSubpath = args.targetSubpath ? normalizeRelInput(String(args.targetSubpath)) : "";
      const targetRel = targetSubpath
        ? ensureMarkdownPath(path.posix.join(targetCategory, targetSubpath, sourceBaseName))
        : ensureMarkdownPath(path.posix.join(targetCategory, sourceBaseName));

      const targetAbs = resolveVaultPath(targetRel).absPath;
      await fs.mkdir(path.dirname(targetAbs), { recursive: true });
      await fs.rename(sourceAbs, targetAbs);
      changedNotes.add(targetRel);

      const notes = await listAllNotes();
      const patched = [];
      for (const relPath of notes) {
        const absPath = resolveVaultPath(relPath).absPath;
        const content = await readText(absPath);
        const replaced = replaceWikiReferences(content, sourceRel, targetRel);
        if (replaced !== content) {
          await writeText(absPath, replaced);
          changedNotes.add(relPath);
          patched.push(relPath);
        }
      }

      return makeResponse({ newPath: targetRel, backlinksPatched: patched.length, patchedFiles: patched });
    }

    if (name === "link_notes") {
      const fromRel = ensureMarkdownPath(normalizeRelInput(args.from));
      const toRel = ensureMarkdownPath(normalizeRelInput(args.to));
      const mode = args.mode === "forward" ? "forward" : "bidirectional";
      const fromAbs = resolveVaultPath(fromRel).absPath;
      const toAbs = resolveVaultPath(toRel).absPath;

      if (!(await pathExists(fromAbs))) {
        throw new Error(`Source note not found: ${fromRel}`);
      }
      if (!(await pathExists(toAbs))) {
        throw new Error(`Target note not found: ${toRel}`);
      }

      const updatedFiles = [];
      const fromContent = await readText(fromAbs);
      const fromLinked = addWikiLinkIfMissing(fromContent, toWikiPath(toRel));
      if (fromLinked.changed) {
        await writeText(fromAbs, fromLinked.content);
        changedNotes.add(fromRel);
        updatedFiles.push(fromRel);
      }

      if (mode === "bidirectional") {
        const toContent = await readText(toAbs);
        const toLinked = addWikiLinkIfMissing(toContent, toWikiPath(fromRel));
        if (toLinked.changed) {
          await writeText(toAbs, toLinked.content);
          changedNotes.add(toRel);
          updatedFiles.push(toRel);
        }
      }

      const graph = await buildLinkGraph();
      const checks = [fromRel, ...(mode === "bidirectional" ? [toRel] : [])].map((relPath) => {
        const z = zettelWarningsFor(relPath, graph);
        return { path: relPath, warnings: z.warnings };
      });

      const warnings = checks.flatMap((entry) => entry.warnings);
      return makeResponse({ updatedFiles, warnings });
    }

    if (name === "audit_links") {
      const scope = args.scope === "changed" ? "changed" : "all";
      const graph = await buildLinkGraph();
      const targetNotes = scope === "changed"
        ? graph.notes.filter((note) => changedNotes.has(note))
        : graph.notes;
      const violations = [];
      for (const relPath of targetNotes) {
        const z = zettelWarningsFor(relPath, graph);
        const missingOut = z.warnings.some((item) => item.code === "missing_outgoing_link");
        const missingIn = z.warnings.some((item) => item.code === "missing_incoming_link");
        if (missingOut || missingIn) {
          violations.push({ path: relPath, missingOut, missingIn });
        }
      }
      return makeResponse({
        scope,
        summary: {
          checked: targetNotes.length,
          violations: violations.length,
          changedTracked: changedNotes.size
        },
        violations
      });
    }

    if (name === "suggest_links") {
      const targetPath = args.path ? ensureMarkdownPath(normalizeRelInput(String(args.path))) : null;
      const apply = Boolean(args.apply);
      const graph = await buildLinkGraph();
      const targets = targetPath ? [targetPath] : graph.notes;
      const suggestions = [];
      const updatedFiles = [];

      for (const relPath of targets) {
        const z = zettelWarningsFor(relPath, graph);
        if (z.linksInCount > 0) {
          continue;
        }
        const candidates = buildBacklinkCandidates(relPath, graph.notes);
        const source = candidates[0] || null;
        if (!source) {
          suggestions.push({ target: relPath, source: null, reason: "no_moc_candidate" });
          continue;
        }
        const suggestion = {
          target: relPath,
          source,
          link: `[[${toWikiPath(relPath)}]]`,
          reason: "missing_incoming_link"
        };
        suggestions.push(suggestion);

        if (apply) {
          const sourceAbs = resolveVaultPath(source).absPath;
          const sourceContent = await readText(sourceAbs);
          const linked = addWikiLinkIfMissing(sourceContent, toWikiPath(relPath));
          if (linked.changed) {
            await writeText(sourceAbs, linked.content);
            changedNotes.add(source);
            updatedFiles.push(source);
          }
        }
      }

      return makeResponse({
        suggestions,
        applied: apply,
        updatedFiles: Array.from(new Set(updatedFiles))
      });
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    return makeErrorResponse(error);
  }
});

async function main() {
  await fs.mkdir(VAULT_ROOT, { recursive: true });
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  // eslint-disable-next-line no-console
  console.error("obsidian-memory MCP failed:", error);
  process.exit(1);
});
