---
name: firefox-devtools-testing
description: Firefox DevTools fallback browser testing workflow. Use after internal Codex Browser / Browser Use / in-app browser is blocked or insufficient for browser-proof, persistent authenticated profiles, console/network checks, screenshots, privileged scripts, prefs, and extension diagnostics.
---

# Firefox DevTools fallback browser testing

## When to use
- Use only after the in-app browser surfaces are blocked or insufficient, or when the user explicitly asks for Firefox DevTools.

## Do first
- Confirm that Browser Use or the in-app browser was tried or is unsuitable.
- Prefer direct `firefox-devtools` MCP tools for new work.
- Record which browser contour is being used and why.
- Summarize launch profile, target URL, and the material browser-proof result.

## Expected result
- A local browser-proof or diagnostics step is completed using the approved Firefox fallback contour.

## Checks
- The request is really about local interactive browser verification.
- The needed profile, URL, or diagnostic scope is explicit.
- Standalone Playwright is used only as a later fallback, not by default.

## Stop when
- Required args are missing.
- The primary browser surfaces are still sufficient and unblocked.
- MCP returns policy or config errors.
- The request would mutate state beyond approved browser diagnostics.

## Ask user when
- The desired site, profile, or browser proof target is unclear.
- Persistent authenticated state would exceed the stated scope.

## Tool map
- `browser_profile_launch`: launch the approved Firefox profile for local browser-proof and diagnostics.
