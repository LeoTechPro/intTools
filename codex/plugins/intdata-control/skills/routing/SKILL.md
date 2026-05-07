---
name: routing
description: Routing registry validation. Используйте для проверки и резолва high-risk agent tool routing перед реальным вызовом.
---

# Routing registry validation

## When to use
- Use when a task depends on route resolution or on validating that the runtime exposes the expected tool surface.

## Do first
- Prefer the routing MCP tools.
- State whether you are validating an existing route or resolving a new one.
- Summarize the resolved route, mismatch, or blocker in worklog or final output.

## Expected result
- The correct route is validated or resolved without guessing.

## Checks
- The requested route id, task class, or surface is explicit.
- Read-only validation remains read-only.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The route definition is ambiguous or drifted.

## Ask user when
- Multiple route candidates remain plausible.
- Resolution would justify mutating surrounding config or workflow.

## Tool map
- `routing_validate`: read-only route verification.
- `routing_resolve`: read-only route resolution for a requested capability.
