---
name: intbrain-memory
description: "Agent-agnostic memory workflow for intbrain: DB-first retrieval (`context/pack`) with controlled fallback and scoped write-back (`context/store`, `graph/link`)."
metadata:
  short-description: "Universal intbrain memory workflow"
---

# IntBrain Memory (Agent-agnostic)

## Purpose

Use `intbrain` as universal memory-core for any agent (Codex, OpenClaw, and future consumers) without vendor-specific logic.

## Contract

1. Always start with DB-first retrieval:
   - `intbrain_context_pack` (preferred) or `POST /api/core/v1/context/pack`
2. Resolve entities when needed:
   - `intbrain_people_resolve`, `intbrain_people_get`, `intbrain_graph_neighbors`
3. Only if `fallback_needed=true`, request markdown fallback.
4. Write-back only through scoped tools:
   - `intbrain_context_store`, `intbrain_graph_link`

## Safety

- Never bypass agent scopes; rely on `X-Agent-Id` + `X-Agent-Key`.
- For write operations, keep payload concise and traceable (`source`, `source_path`, `chunk_kind`).
- Do not hardcode OpenClaw/Codex in memory payloads or tags.

## Expected Output Pattern

- Brief answer from `context/pack`.
- Explicit note when fallback is required.
- If write-back executed, report what was written and why.

