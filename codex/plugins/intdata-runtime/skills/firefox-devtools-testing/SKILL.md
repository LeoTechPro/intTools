---
name: firefox-devtools-testing
description: Firefox DevTools fallback browser testing workflow. Use after internal Codex Browser / Browser Use / in-app browser is blocked or insufficient for browser-proof, persistent authenticated profiles, console/network checks, screenshots, privileged scripts, prefs, and extension diagnostics.
---

# Firefox DevTools Fallback Browser Testing

Use this skill only as fallback after trying internal Codex Browser / Browser Use / in-app browser, or when the user explicitly asks for Firefox DevTools. It covers local browser-proof and authenticated manual-site checks on the agent-owned Windows workstation.

## Routing

- Default chain: internal Codex Browser / Browser Use / in-app browser -> `firefox-devtools` -> `chrome-devtools` -> standalone Playwright.
- Local PC fallback: use the configured `firefox-devtools` MCP server.
- Authenticated sites: use a persistent Firefox profile so existing manual login/session state can be inspected. Do not default to Playwright isolated contexts for this case.
- Privileged local Firefox is allowed for agents: `evaluate_script`, `evaluate_privileged_script`, `set_firefox_prefs`, `get_firefox_prefs`, and extension tools are in scope when needed.
- Screenshots must be saved to a file with `screenshot_page({ saveTo })`.
- Network and console evidence must use `list_network_requests`, `get_network_request`, and `list_console_messages`.
- Remote, VDS, CI, headless, and reproducible E2E: standalone Playwright remains the final fallback. Use explicit `storageState` or `userDataDir` only when session persistence is intentionally required.

## Evidence Checklist

- Capture the tested URL, profile/context, and exact account/session assumption.
- Save at least one screenshot file for visual evidence.
- Check console messages for runtime errors.
- Check network requests for failed API/document requests.
- Record which browser contour was used and why: Browser Use default, Firefox fallback, Chrome fallback, or standalone Playwright final fallback.

## Tool cards

### browser_profile_launch
- Когда: legacy compatibility only, when a runtime MCP caller still needs to launch an allowed dedicated Firefox profile before migrating to the `firefox-devtools-testing` workflow.
- Required inputs: `confirm_mutation`, `issue_context`, `profile`
- Optional/schema inputs: `cwd`, `timeout_sec`, `args`
- Режим: mutating, deprecated compatibility surface
- Approval / issue requirements: owner approval, `confirm_mutation=true`, and `issue_context=INT-*` are required. Do not use unattended mutation.
- Не использовать когда: a configured `firefox-devtools` MCP session is available for direct local browser-proof, the target profile is unknown, the task needs production/destructive action without explicit owner approval, or remote/CI reproducibility is more important than a persistent local session.
- Пример вызова: `{"name":"browser_profile_launch","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "profile": "firefox-default"}}`
- Fallback/blocker: if required args are unknown, MCP returns policy/config error, or the request needs mutation without approval, stop and report a blocker instead of using shell fallback. Prefer direct `firefox-devtools` MCP tools for new work.
