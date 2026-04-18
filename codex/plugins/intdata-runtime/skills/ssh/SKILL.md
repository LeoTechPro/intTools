---
name: intdata-runtime-ssh
description: Use for intData SSH transport resolution and SSH host diagnostics through intData Runtime MCP tools.
---

# intData Runtime: SSH

Use this before connecting to canonical hosts or when diagnosing transport selection.

## Tools

- `ssh_resolve`
- `ssh_host`

## Rules

- Resolve first, then inspect host diagnostics.
- Canonical hosts include prod `vds.punkt-b.pro` and dev `vds.intdata.pro`.
- Do not call resolver scripts directly while MCP is available.

## Blockers

- Unknown host alias.
- Resolver reports unsupported platform or missing transport.
- Task asks for interactive shell without explicit owner approval.

## Fallback

Direct SSH/resolver wrappers require MCP blocker and owner approval.

## Examples

- Resolve: `ssh_resolve(cwd="D:/int/tools", host="dev", mode="auto", json=true)`
- Host diagnostics: `ssh_host(cwd="D:/int/tools", host="dev", args=["--json"])`
