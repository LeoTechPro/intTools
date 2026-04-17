# intdata-runtime plugin skill pointer

Use this plugin for runtime/host transport and browser profile operations in `@int-tools`.

## Tools
- `host_preflight`
- `host_verify`
- `host_bootstrap`
- `recovery_bundle`
- `ssh_resolve`
- `ssh_host`
- `browser_profile_launch`

## Guardrails
- Mutating operations require `confirm_mutation=true`.
- Mutating operations require `issue_context=INT-*`.
- Structured args/enums only; no arbitrary shell passthrough.

## Migration note
- Replaces removed plugins: `intdata-host`, `intdata-ssh`, `intdata-browser`.
- Do not use removed tool names/IDs in instructions.
