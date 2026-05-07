---
name: openspec-read
description: OpenSpec read-only discovery. Используйте для просмотра, list/status/validate и проверки source-of-truth без изменения OpenSpec lifecycle.
---

# OpenSpec read-only discovery

## When to use
- Use for OpenSpec listing, show, validation, status, and enriched instructions without changing lifecycle state.

## Do first
- Prefer the OpenSpec MCP tools exposed through `intdata-control`.
- Keep the request read-only; if the user wants lifecycle edits, switch to `openspec-mutation`.
- Confirm the relevant repo root or artifact name before calling tools.
- Summarize material tool results such as item names, status, counts, and validation verdicts.

## Expected result
- The requested OpenSpec artifact is discovered or checked without mutating it.

## Checks
- Use the narrowest tool for the question.
- `item` or `artifact` identifiers are known when required.
- `cwd` points at the owning repo when repo-local OpenSpec is expected.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The user actually needs a lifecycle mutation.
- The artifact or source repo is ambiguous.

## Ask user when
- More than one spec or change could match the request.
- The work needs promotion from read-only discovery to mutation.

## Tool map
- `openspec_list`: read-only; optional `cwd`, `timeout_sec`, `specs`.
- `openspec_show`: read-only; input `item`; optional `cwd`, `timeout_sec`, `json`.
- `openspec_validate`: read-only; optional `cwd`, `timeout_sec`, `item`, `strict`.
- `openspec_status`: read-only; optional `cwd`, `timeout_sec`, `item`.
- `openspec_instructions`: read-only; input `artifact`; optional `cwd`, `timeout_sec`, `args`.
