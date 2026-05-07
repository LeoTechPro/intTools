---
name: ssh
description: Runtime SSH routes. Используйте ssh_resolve как единую canonical intData Runtime transport surface.
---

# Runtime SSH routes

## When to use
- Use for read-only resolution of the canonical SSH route for a logical host or contour.

## Do first
- Confirm the logical host name and whether you need destination-only or full route details.
- Prefer `ssh_resolve`; do not guess transport hops from memory.
- Summarize the resolved route or blocker in worklog or final output.

## Expected result
- The canonical route for the requested host is resolved without side effects.

## Checks
- `host` is explicit.
- The task is inspection-only.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- The logical host is ambiguous.

## Ask user when
- More than one host alias could be intended.
- The user actually wants to execute remote commands rather than resolve routing.

## Tool map
- `ssh_resolve`: read-only; input `host`; optional `cwd`, `timeout_sec`, `mode`, `json`, `destination_only`.
