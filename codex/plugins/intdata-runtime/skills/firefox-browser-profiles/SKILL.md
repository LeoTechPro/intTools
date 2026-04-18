---
name: intdata-runtime-firefox-browser-profiles
description: Use for launching dedicated Firefox MCP browser profiles for frontend/browser proof.
---

# intData Runtime: Firefox Browser Profiles

Use this when browser proof is required for `/int/*` tasks.

## Tools

- `browser_profile_launch`

## Rules

- Dedicated Firefox MCP profiles are the default browser runtime.
- Owner Chrome is fallback only after documenting the blocker.
- Launch is mutating/interactive and requires `confirm_mutation=true`, `issue_context="INT-*"`, and an allowed `profile`.

## Blockers

- No browser proof is needed for the task.
- Unknown profile enum.
- Existing profile launch conflict.

## Fallback

Attach to owner Chrome only with explicit owner approval and recorded reason.

## Examples

- Launch default: `browser_profile_launch(cwd="D:/int/tools", profile="firefox-default", confirm_mutation=true, issue_context="INT-226")`
- Launch with URL: `browser_profile_launch(cwd="D:/int/tools", profile="firefox-default", args=["--start-url", "http://127.0.0.1:3000"], confirm_mutation=true, issue_context="INT-226")`
