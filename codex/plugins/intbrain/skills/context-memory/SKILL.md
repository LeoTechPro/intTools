---
name: intbrain-context-memory
description: Use for IntBrain context packs, memory search, context store, and graph link operations through MCP tools.
---

# IntBrain: Context and Memory

Use this for retrieval, memory search, scoped context write-back, and graph links.

## Tools

- `intbrain_context_pack`
- `intbrain_memory_search`
- `intbrain_context_store`
- `intbrain_graph_link`

## Rules

- Retrieval/search requires known `owner_id`; do not guess it.
- `context_store` and `graph_link` are writes and require `confirm_mutation=true` and `issue_context="INT-*"`.
- Prefer source, source_path, source_hash, tags, and confidence/provenance when writing.

## Blockers

- Missing `owner_id`.
- Missing write approval for store/link.
- IntBrain auth/env unavailable.

## Fallback

Direct API/CLI calls require MCP blocker and owner approval.

## Examples

- Context: `intbrain_context_pack(owner_id=1, query="current agent tool plane", limit=5)`
- Search: `intbrain_memory_search(owner_id=1, query="INT-226", limit=10)`
- Store: `intbrain_context_store(owner_id=1, kind="note", title="...", text_content="...", confirm_mutation=true, issue_context="INT-226")`
