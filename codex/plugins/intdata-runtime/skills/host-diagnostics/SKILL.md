---
name: intdata-runtime-host-diagnostics
description: Use for intData Runtime host preflight, host verification, bootstrap, and recovery bundle workflows.
---

# intData Runtime: Host Diagnostics

Use this for local Codex host/runtime health checks and guarded recovery.

## Tools

- `host_preflight`
- `host_verify`
- `host_bootstrap`
- `recovery_bundle`

## Rules

- `host_preflight` and `host_verify` are the default read-only diagnostics.
- `host_bootstrap` and `recovery_bundle` are mutating and require `confirm_mutation=true` and `issue_context="INT-*"`.
- Use structured `args`; do not call shell wrappers directly while MCP is available.

## Blockers

- Missing issue for bootstrap or recovery.
- Unknown host/runtime target.
- MCP tool missing from model context; request it through tool discovery.

## Fallback

Direct wrappers require recorded MCP blocker and owner approval.

## Examples

- Preflight: `host_preflight(cwd="D:/int/tools", json=true)`
- Verify: `host_verify(cwd="D:/int/tools", args=["--json"])`
- Guarded bootstrap: `host_bootstrap(cwd="D:/int/tools", confirm_mutation=true, issue_context="INT-226")`
