---
name: intdata-control-routing
description: Use for high-risk agent tool routing registry validation and logical intent resolution.
---

# intData Control: Routing

Use this before changing or trusting high-risk wrapper paths, publish/deploy entrypoints, SSH/browser launchers, sync gates, or intdb bindings.

## Tools

- `routing_validate`
- `routing_resolve`

## Rules

- Validate with `strict=true` before and after routing-related changes.
- Resolve logical intent before choosing direct wrapper paths.
- Do not use removed plugin IDs or stale tool names.

## Blockers

- Missing engine, missing adapter, adapter drift, unsupported platform, unknown intent, or ambiguous intent.
- Registry validation failure.

## Fallback

Use skills as fallback metadata only when the registry explicitly approves that fallback.

## Examples

- Validate: `routing_validate(cwd="D:/int/tools", strict=true, json=true)`
- Resolve publish: `routing_resolve(cwd="D:/int/tools", intent="publish:data", platform="windows", json=true)`
- Resolve SSH: `routing_resolve(cwd="D:/int/tools", intent="ssh", platform="windows", json=true)`
