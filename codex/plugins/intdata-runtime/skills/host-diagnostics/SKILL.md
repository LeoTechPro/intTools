---
name: host-diagnostics
description: Runtime host diagnostics. Используйте для host_preflight, host_verify, bootstrap и recovery bundle проверок runtime окружения.
---

# Runtime host diagnostics

## When to use
- Use for runtime readiness checks, helper verification, approved bootstrap, and recovery bundle collection.

## Do first
- Confirm whether the request is read-only diagnostics or mutating maintenance.
- Prefer the runtime MCP tools.
- Summarize readiness verdicts, verification results, bootstrap changes, or recovery bundle output.

## Expected result
- One clear host diagnostics action is completed for the intended contour.

## Checks
- Read-only tasks use `host_preflight` or `host_verify`.
- Mutating tasks include approval and `issue_context=INT-*`.
- The target host or contour is explicit.

## Stop when
- Required args are missing.
- MCP returns policy or config errors.
- Mutation is requested without approval.
- The host contour is ambiguous.

## Ask user when
- More than one host or helper contour could match.
- Bootstrap or recovery bundle creation changes a shared environment unexpectedly.

## Tool map
- `host_preflight`: read-only local runtime readiness check.
- `host_verify`: read-only helper contour verification.
- `host_bootstrap`: mutating bootstrap or update; approval required.
- `recovery_bundle`: mutating recovery artifact collection; approval required.
