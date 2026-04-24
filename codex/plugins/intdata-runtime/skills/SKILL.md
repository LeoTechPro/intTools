---
name: intdata-runtime
description: Internal int-tools skill entrypoint for the intdata-runtime plugin. Use as the router for host diagnostics, SSH routes, fallback Firefox DevTools browser testing, and runtime vault maintenance.
---

# intData Runtime Router

- Use this skill for host diagnostics, SSH route checks, fallback Firefox DevTools browser testing, and vault maintenance.
- Default browser-proof is internal Codex Browser / Browser Use / in-app browser. Use `firefox-devtools-testing` only after Browser Use is blocked or insufficient; fallback after that is `chrome-devtools`, then standalone Playwright.
- Runtime, interactive, and destructive actions require explicit owner approval and issue context.
- Start with read-only diagnostics and dry-run by default.

## Capability skills

- `host-diagnostics`: Runtime host diagnostics.
- `ssh`: Runtime SSH routes.
- `firefox-devtools-testing`: Firefox DevTools fallback browser testing and browser-proof workflow.
- `vault-maintenance`: Runtime vault maintenance.

## General rules

- Select the capability skill first, then the concrete tool card.
- Do not call mutating/high-risk tools without owner approval, `confirm_mutation=true`, and `issue_context=INT-*`.
- If required args are unknown, stop as blocker and do not replace MCP with direct shell fallback.
