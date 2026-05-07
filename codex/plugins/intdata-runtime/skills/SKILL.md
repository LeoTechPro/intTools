---
name: intdata-runtime
description: Internal int-tools skill entrypoint for the intdata-runtime plugin. Use as the router for host diagnostics, SSH routes, fallback Firefox DevTools browser testing, and runtime vault maintenance.
---

# intData Runtime

## When to use
- Use for runtime host diagnostics, SSH route discovery, approved Firefox fallback browser testing, and runtime vault maintenance.

## Do first
- Prefer the plugin MCP surface for `intdata-runtime`.
- Pick the narrowest leaf skill before calling tools.
- Confirm whether the task is read-only, diagnostic, or mutating maintenance.
- Summarize material tool results in worklog or final response because raw payloads may be hidden in the UI.

## Expected result
- The correct runtime surface is used with clear target host, browser contour, or vault scope.

## Checks
- The target contour or host is explicit.
- Read-only diagnostics stay read-only.
- Mutating maintenance has explicit approval and issue context.

## Stop when
- Required args are unknown.
- MCP returns policy or config errors.
- The request needs mutation without approval.
- The target contour or runtime scope is ambiguous.

## Ask user when
- More than one host, browser contour, or vault target could match.
- A maintenance action would mutate shared runtime state.

## Skill map
- `host-diagnostics`: preflight, verify, bootstrap, recovery bundle.
- `ssh`: canonical SSH route discovery.
- `firefox-devtools-testing`: approved fallback browser testing after in-app surfaces.
- `vault-maintenance`: sanitize or GC runtime vault data.
